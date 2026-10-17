FROM nginxinc/nginx-unprivileged:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY index.html app.js queue.js style.css sw.js manifest.webmanifest icon.svg /usr/share/nginx/html/
