/*
 * 自毁型 Service Worker
 * ------------------------------------------------------------
 * 旧版（Jekyll/Chirpy）站点开启了 PWA 离线缓存，向访问者浏览器
 * 注册过 Service Worker。站点迁移到 Sphinx 后，旧 SW 仍会从本地
 * 缓存喂旧页面，导致访客长期看到旧主题。
 *
 * 本文件占住 /sw.js 这个注册位：浏览器下次更新检查时会拿到本脚本，
 * 安装后立即清空全部 Cache Storage 并自我注销，之后再无 SW 拦截，
 * 访客即可看到真实的新版站点。
 */
self.addEventListener('install', () => {
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    (async () => {
      const keys = await caches.keys();
      await Promise.all(keys.map((key) => caches.delete(key)));
      await self.registration.unregister();
      // 让所有受控页面立刻脱离旧 SW
      const clients = await self.clients.matchAll({ type: 'window' });
      clients.forEach((client) => client.navigate(client.url));
    })()
  );
});
