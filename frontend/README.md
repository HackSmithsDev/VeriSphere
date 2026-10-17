# VeriSphere frontend

The frontend is a responsive, web-only React application built with Vite. It serves the public landing and registration experience; student curriculum, evidence upload, attendance, marks, achievement, and shareable portfolio views; faculty workspaces scoped to courses assigned by an administrator; and administrator account, assignment, and reporting tools. Shared portfolio links open as public web pages that can be printed or saved as PDF. No native mobile client is included.

## Development

```sh
npm ci
npm run dev
```

The Vite server listens on port 5176 and proxies API calls to `http://127.0.0.1:8088`. Start the backend separately; see the repository [README](../README.md).

`VITE_API_URL` defaults to `/api/v1`, which uses the same-origin Nginx proxy. For a separately hosted API, set it to the full HTTPS API base, such as `https://verisphere-api.hacksmiths.dev/api/v1`. An older HTTP origin-only value is upgraded to HTTPS and given the `/api/v1` prefix when the site is loaded over HTTPS.

## Production container

`npm run build` creates the static application. The Nginx image serves it on port 5176, proxies `/api` and `/health` to the Compose backend, and falls back to `index.html` for the client-side app.
