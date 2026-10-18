const CACHE="jux-shell-v3";
const ASSETS=["/","/index.html","/style.css","/app.js","/queue.js","/manifest.webmanifest","/icon.svg"];
self.addEventListener("install",e=>e.waitUntil(caches.open(CACHE).then(c=>c.addAll(ASSETS))));
self.addEventListener("activate",e=>e.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(k=>k.startsWith("jux-shell-")&&k!==CACHE).map(k=>caches.delete(k))))));
self.addEventListener("fetch",e=>{
  const url=new URL(e.request.url);
  if(e.request.method!=="GET" || url.origin!==self.location.origin || !ASSETS.includes(url.pathname)) return;
  e.respondWith(caches.match(e.request).then(cached=>cached||fetch(e.request)));
});
