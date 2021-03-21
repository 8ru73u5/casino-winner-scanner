class NotificationComponent {
    static $hook = document.getElementById('notifications-container');
    static $template = `
      <div class="notification box">
        <div class="n--uptime"></div>
        <div>
          <h3 class="title"><span class="n--emoji"></span> <a class="n--game" target="_blank"></a></h3>
        </div>
        <div class="content">
          <div class="notification-item">
            <div class="title">Time:</div>
            <div class="n--time"></div>
          </div>
          <div class="notification-item">
            <div class="title">Score:</div>
            <div class="n--score"></div>
          </div>
          <div class="notification-item">
            <div class="title">Bet:</div>
            <div class="n--bet"></div>
          </div>
          <div class="notification-item">
            <div class="title">Tips:</div>
            <div>
              <ul class="n--tips"></ul>
            </div>
          </div>
        </div>
      </div>
    `;

    static $soundMinUptime = Infinity;
    static $notificationSound = new Audio('static/sounds/snap.ogg');

    constructor(data) {
        const template = document.createElement('template');
        template.innerHTML = NotificationComponent.$template;

        this.root = template.content.firstElementChild.cloneNode(true);

        this.id = data.id;
        this.score = data.score;
        this.soundPlayed = false;

        this._setNotificationData(data);
    }

    _setUptime(uptimeSeconds, uptimeFormatted) {
        this.root.querySelector('.n--uptime').innerText = uptimeFormatted;

        if (uptimeSeconds < 60) {
            // Just added
        } else if (uptimeSeconds < 150) {
            this.root.classList.add('uptime-short');
        } else if (uptimeSeconds < 300) {
            this.root.classList.remove('uptime-short');
            this.root.classList.add('uptime-medium');
        } else {
            this.root.classList.remove('uptime-medium');
            this.root.classList.add('uptime-long');
        }

        if (uptimeSeconds > NotificationComponent.$soundMinUptime && !this.soundPlayed) {
            NotificationComponent.$notificationSound.play().finally(() => this.soundPlayed = true);
        }
    }

    _setMatchTime(matchTime) {
        this.root.querySelector('.n--time').innerText = matchTime;
    }

    _setScore(score) {
        if (this.score !== score) {
            this.root.classList.add('updated');
            setTimeout(() => this.root.classList.remove('updated'), 1000);
        }

        let formattedScore = score;
        const individualScores = score.split(':')
            .map((x) => parseInt(x))
            .filter((x) => !isNaN(x));

        if (individualScores.length === 2) {
            formattedScore = `${score} (${individualScores[0] + individualScores[1]})`;
        }

        this.root.querySelector('.n--score').innerText = formattedScore;
        this.score = score;
    }

    _setNotificationData(data) {
        this.updateNotificationData(data);

        this.root.querySelector('.n--game').href = data.link;

        this.root.querySelector('.n--emoji').innerHTML = data.sport_name;
        this.root.querySelector('.n--game').innerText = `${data.first_team} vs ${data.second_team}`;
        this.root.querySelector('.n--bet').innerText = data.bet_name;

        data.tips.forEach(({name, odds, selection_id}) => {
            const li = document.createElement('li');
            li.innerText = ` ${name} (${odds})`;

            const iconSpan = document.createElement('span');

            iconSpan.classList.add('icon', 'has-text-info');
            iconSpan.setAttribute('role', 'button');
            iconSpan.style.setProperty('cursor', 'pointer');
            iconSpan.addEventListener('click', e => {
                e.preventDefault();

                saveBetDataToLocalStorage({
                    eventName: `${data.first_team} vs ${data.second_team}`,
                    betName: data.bet_name,
                    tipName: name,
                    odds: odds,
                    selectionId: selection_id
                });

                window.open('/place_bet');
            });

            const icon = document.createElement('i');
            icon.classList.add('fas', 'fa-shopping-cart');

            iconSpan.appendChild(icon);
            li.appendChild(iconSpan);

            this.root.querySelector('.n--tips').appendChild(li);
        });
    }

    updateNotificationData(data) {
        this._setUptime(data.uptime_seconds, data.uptime);
        this._setMatchTime(data.time);
        this._setScore(data.score);
    }

    attachToDOM() {
        this.root.classList.add('added');
        setTimeout(() => this.root.classList.remove('added'), 3000);

        NotificationComponent.$hook.prepend(this.root);
    }

    removeFromDOM() {
        this.root.classList.add('removed');
        this.root.style.setProperty('max-height', this.root.offsetHeight);
        setTimeout(() => NotificationComponent.$hook.removeChild(this.root), 3000);
    }

    static async getSoundMinUptime() {
        let response;
        try {
            response = await axios.get('/config/option/4');
        } catch (e) {
            console.error('While fetching sound min uptime:', e);
        }

        NotificationComponent.$soundMinUptime = response.data.value;
    }
}
