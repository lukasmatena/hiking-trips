# Hiking Trips - Frontend

This directory contains the user-facing application built with **Vite** and **TypeScript**. It is hosted on **Firebase Hosting**.

## Project Structure & Configuration

This folder mixes application code with deployment configuration. Here is what you need to know about the key files:

* **`vite.config.ts`**: Configures the build. It also sets up a **Proxy** (`/api` -> `localhost:8000`) so local development works without CORS issues.
* **`firebase.json`**: The hosting configuration for production (Security headers, clean URLs, etc.).
* **`package.json`**: Contains custom deployment scripts that handle build modes and `robots.txt` swapping.
* **`public/`**: Static assets copied 1:1 to `dist/`.

---

## Cheat sheet

#### Local development
```npm run dev```

What this does:
- Start Vite dev server
- proxies /api requests to local Python backend

```npm run build```

Bundles the app and copies everything to dist.


#### Deploy to Stage
```firebase login && npm run deploy:stage```

What this does:
- Renames dist/robots.stage.txt -> dist/robots.txt (Blocks search engines).
- Deletes dist/robots.prod.txt.
- Deploys to the Stage Firebase project.


#### Deploy to Production

```firebase login && npm run deploy:prod```


#### Logout from firebase

```firebase logout```
