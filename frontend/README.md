# VeriSphere frontend

The frontend is a responsive React application built with Vite. It serves the public landing and registration experience, student learning-path screens, and role-specific faculty and administrator workspaces.

## Development

```sh
npm ci
npm run dev
```

The Vite server listens on port 5176 and proxies API calls to `http://127.0.0.1:8088`. Start the backend separately; see the repository [README](../README.md).

## Production container

`npm run build` creates the static application. The Nginx image serves it on port 5176, proxies `/api` and `/health` to the Compose backend, and falls back to `index.html` for the client-side app.
