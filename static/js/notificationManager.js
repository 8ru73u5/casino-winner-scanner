class NotificationManager {
    constructor() {
        this.notifications = [];
        this.notificationsIds = new Set();
        this.updateLock = false;
    }

    async fetchNotifications() {
        if (this.updateLock) {
            return;
        } else {
            this.updateLock = true;
        }

        let response;

        try {
            response = await axios.get('/notifications');
        } catch (e) {
            console.error('While fetching notifications:', e);
            this.updateLock = false;
            return;
        }

        let newNotificationsData = [];
        let updatedNotificationsData = [];
        let removedNotifications = [];

        let responseNotificationIds = new Set();

        response.data.notifications.forEach(nData => {
            responseNotificationIds.add(nData.id);

            if (this.notificationsIds.has(nData.id)) {
                updatedNotificationsData.push(nData);
            } else {
                newNotificationsData.push(nData);
            }
        });

        this.notifications.forEach(nComponent => {
            if (!responseNotificationIds.has(nComponent.id)) {
                removedNotifications.push(nComponent);
            }
        });

        this._addNotifications(newNotificationsData.sort((a, b) => b.uptime_seconds - a.uptime_seconds));
        this._updateNotifications(updatedNotificationsData);
        this._removeNotifications(removedNotifications);

        this.updateLock = false;

        if (response.data.notifications.length !== this.notifications.length && response.data.notifications.length !== this.notificationsIds.size) {
            alert(`O kurwa! ${response.data.notifications.length}, ${this.notifications.length}, ${this.notificationsIds.size}`);
        }
    }

    _addNotifications(notificationsData) {
        notificationsData.forEach(nData => {
            const notification = new NotificationComponent(nData);
            notification.attachToDOM();

            this.notifications.push(notification);
            this.notificationsIds.add(notification.id);
        })
    }

    _updateNotifications(notificationsData) {
        notificationsData.forEach(nData => {
            const existingNotification = this.notifications.find(n => n.id === nData.id);

            if (existingNotification) {
                existingNotification.updateNotificationData(nData);
            }
        });
    }

    _removeNotifications(notificationsComponents) {
        const removedNotificationIds = new Set();

        notificationsComponents.forEach(nComponent => {
            nComponent.removeFromDOM();
            removedNotificationIds.add(nComponent.id);
            this.notificationsIds.delete(nComponent.id);
        });

        this.notifications = this.notifications.filter(n => !removedNotificationIds.has(n.id));
    }
}
