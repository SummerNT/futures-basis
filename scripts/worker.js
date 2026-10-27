// futures-basis cron worker
//
// Purpose: give GitHub Actions a reliable "alarm clock".
//   - Cron  : 30 8 * * 1-5 (UTC) = 16:30 Beijing, Mon-Fri
//   - Manual: GET /trigger?key=<TRIGGER_KEY>
//
// Required environment variables (Settings -> Variables and Secrets):
//   GH_TOKEN     fine-grained PAT, Actions: Read and write, this repo only  [secret]
//   REPO         SummerNT/futures-basis
//   TRIGGER_KEY  any random string, protects the manual endpoint           [secret]
// Optional:
//   WORKFLOW     daily.yml (default)
//   BRANCH       main (default)

export default {
  async scheduled(controller, env, ctx) {
    ctx.waitUntil(run(env));
  },

  async fetch(request, env) {
    const url = new URL(request.url);

    if (url.pathname === "/trigger") {
      if (env.TRIGGER_KEY && url.searchParams.get("key") !== env.TRIGGER_KEY) {
        return text("403 forbidden: missing or wrong key", 403);
      }
      const msg = await run(env);
      return text(msg, msg.includes(" OK ") ? 200 : 502);
    }

    return text(
      "futures-basis worker\n\n" +
        "GET /trigger?key=...   trigger one refresh now\n" +
        "cron                  weekdays 16:30 Beijing time\n"
    );
  },
};

async function run(env) {
  const repo = env.REPO;
  const workflow = env.WORKFLOW || "daily.yml";
  const branch = env.BRANCH || "main";

  if (!repo || !env.GH_TOKEN) {
    return "ERR missing REPO or GH_TOKEN";
  }

  const res = await fetch(
    `https://api.github.com/repos/${repo}/actions/workflows/${workflow}/dispatches`,
    {
      method: "POST",
      headers: {
        authorization: `Bearer ${env.GH_TOKEN}`,
        accept: "application/vnd.github+json",
        "user-agent": "futures-basis-worker",
        "content-type": "application/json",
      },
      body: JSON.stringify({ ref: branch }),
    }
  );

  const stamp = new Date(Date.now() + 8 * 3600 * 1000)
    .toISOString()
    .slice(0, 16)
    .replace("T", " ");

  if (res.status === 204) {
    return `${stamp} (Beijing) OK triggered ${repo}/${workflow}@${branch}`;
  }

  const body = (await res.text()).slice(0, 300);
  return `${stamp} (Beijing) FAIL ${res.status}\n${body}`;
}

function text(body, status = 200) {
  return new Response(body, {
    status,
    headers: {
      "content-type": "text/plain; charset=utf-8",
      "cache-control": "no-store",
    },
  });
}
