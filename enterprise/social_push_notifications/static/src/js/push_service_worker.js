/* eslint-env serviceworker */
/* eslint-disable no-restricted-globals */

import { initializeApp } from "https://www.gstatic.com/firebasejs/10.13.2/firebase-app.js";
import { getMessaging, onBackgroundMessage } from "https://www.gstatic.com/firebasejs/10.13.2/firebase-messaging-sw.js";

const getFirebaseConfig = () => {
    const params = new URLSearchParams(self.location.search);
    return {
        appId: params.get("appId"),
        apiKey: params.get("apiKey"),
        projectId: params.get("projectId"),
        messagingSenderId: params.get("messagingSenderId"),
    };
};

// Initialize the Firebase app in the service worker by passing the config in the URL.
const app = initializeApp(getFirebaseConfig());
const messaging = getMessaging(app);

// Add an event listener to handle notification clicks
self.addEventListener('notificationclick', function (event) {
    if (event.action === 'close') {
        event.notification.close();
    } else if (event.notification.data.target_url && '' !== event.notification.data.target_url.trim()) {
        // user clicked on the notification itself or on the 'open' action
        // clients is a reserved variable in the service worker context.
        // check https://developer.mozilla.org/en-US/docs/Web/API/Clients/openWindow

        clients.openWindow(event.notification.data.target_url);
    }
});

// Retrieve an instance of Firebase Messaging so that it can handle background messages
// This line HAS to stay after the event listener or it will break it
// https://stackoverflow.com/questions/50869015/firefox-not-opening-window-in-service-worker-for-push-message

onBackgroundMessage(messaging, function (payload) {
    const options = {
        body: payload.notification.body,
        icon: payload.notification.image
    };
    if (payload.data && payload.data.target_url) {
        options.data = {
            target_url: payload.data.target_url
        };
    }
    return self.registration.showNotification(payload.notification.title, options);
});
