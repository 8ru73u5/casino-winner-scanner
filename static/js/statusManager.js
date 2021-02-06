class StatusManager {
    constructor() {
        this.eventCountElement = document.getElementById('status-events');
        this.notificationCountElement = document.getElementById('status-notifications');
        this.heavyLoadElement = document.getElementById('status-heavy-load');
        this.errorElement = document.getElementById('status-error');

        setInterval(async () => await this.getAppStatus(), 5000);
    }

    async getAppStatus() {
        let response;

        try {
            response = await axios.get('/status');
        } catch (e) {
            console.error('While fetching status:', e);
            return;
        }

        this.eventCountElement.innerText = response.data.status.events;
        this.notificationCountElement.innerText = response.data.status.notifications;
        this.heavyLoadElement.innerText = response.data.heavy_load ? 'yes' : 'no';
        this.errorElement.innerText = response.data.error ? 'yes' : 'no';

        if (response.data.error) {
            this.errorElement.setAttribute('title', response.data.error.error_class);
        } else {
            this.errorElement.removeAttribute('title');
        }
    }
}

const statusManager = new StatusManager();
