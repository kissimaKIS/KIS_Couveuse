const CACHE_NAME = "couveuse-cache-v1";

self.addEventListener("install", (event) => {
    self.skipWaiting();
});

self.addEventListener("activate", (event) => {
    event.waitUntil(clients.claim());
});

// Stratégie "network first, fallback cache" : toujours essayer le serveur
// local en premier (les données changent souvent), et retomber sur le cache
// uniquement si le serveur est injoignable (ex. app mobile hors connexion Wi-Fi).
self.addEventListener("fetch", (event) => {
    event.respondWith(
        fetch(event.request)
            .then((response) => {
                const clone = response.clone();
                caches.open(CACHE_NAME).then((cache) => cache.put(event.request, clone));
                return response;
            })
            .catch(() => caches.match(event.request))
    );
});
