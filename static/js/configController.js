class ConfigItemComponent {
    static $TOUCH_EVENTS = new Set();

    constructor(data, template, prefix) {
        if (this.constructor === ConfigItemComponent) {
            throw new Error('Cannot initialize abstract class ConfigItemComponent');
        }

        const itemTemplate = document.createElement('template');
        itemTemplate.innerHTML = template;

        this.root = itemTemplate.content.firstElementChild.cloneNode(true);
        this.data = data;

        this._nameSlot = this.root.querySelector(`.${prefix}-name`);
        this._triggerTimeInput = this.root.querySelector(`.${prefix}-trigger-time`);
        this._isEnabledCheckbox = this.root.querySelector(`.${prefix}-is-enabled`);

        this._initializeComponent();
    }

    _initializeComponent() {
        this._nameSlot.innerHTML = this.data.name;
        this._isEnabledCheckbox.checked = this.data.is_enabled;

        if (this._triggerTimeInput) {
            if (this.data.trigger_time) {
                this._triggerTimeInput.value = this.data.trigger_time;
            } else {
                this._triggerTimeInput.setAttribute('readonly', '');
            }
        }
    }

    _initializeListeners(url) {
        let interactiveElements = [this._isEnabledCheckbox];
        if (this._triggerTimeInput) {
            interactiveElements.push(this._triggerTimeInput);
        }

        interactiveElements.forEach(element => {
            element.addEventListener('change', event => {
                event.preventDefault();
                this.patchComponent(url);
            });
        });
    }

    patchComponent(url) {
        let params = {
            is_enabled: this._isEnabledCheckbox.checked,
        };

        if (this._triggerTimeInput) {
            const triggerTime = this._triggerTimeInput.value;
            params.trigger_time = triggerTime.length === 0 ? null : triggerTime;
        }

        params = {...this.data, ...params};
        delete params.name;

        axios.patch(url, params).catch(e => console.error(e));
    }

    _initializeTriggerTimeInputClickListeners(url) {
        this._triggerTimeInput.addEventListener('click', event => {
            event.preventDefault();

            if (event.ctrlKey) {
                this._handleTriggerTimeInputClick(url);
            }
        });

        ['touchstart', 'touchend', 'touchcancel'].forEach(eventName => {
            this._triggerTimeInput.addEventListener(eventName, event => {
                event.preventDefault();

                if (event.type === 'touchstart') {
                    const touchId = event.touches[0].identifier;
                    ConfigItemComponent.$TOUCH_EVENTS.add(touchId);

                    let touchTime = 0;

                    const touchTimeWatch = setInterval(() => {
                        touchTime += 100;

                        if (!ConfigItemComponent.$TOUCH_EVENTS.has(touchId)) {
                            clearInterval(touchTimeWatch);
                        }

                        if (touchTime >= 1000) {
                            clearInterval(touchTimeWatch);
                            window.navigator.vibrate(50);
                            this._handleTriggerTimeInputClick(url);
                        }
                    }, 100);
                } else if (event.type === 'touchend' || event.type === 'touchcancel') {
                    if (!this._triggerTimeInput.hasAttribute('readonly')) {
                        this._triggerTimeInput.focus();
                    }

                    Object.values(event.changedTouches)
                        .map(touch => touch.identifier)
                        .forEach(touchId => ConfigItemComponent.$TOUCH_EVENTS.delete(touchId));
                }
            });
        });
    }

    _handleTriggerTimeInputClick(url) {
        if (this._triggerTimeInput.hasAttribute('readonly')) {
            this._triggerTimeInput.removeAttribute('readonly');
            this._triggerTimeInput.focus();
        } else {
            this._triggerTimeInput.value = '';
            this._triggerTimeInput.setAttribute('readonly', '');
            this.patchComponent(url);
        }
    }

    static clearConfigItemList(listElement) {
        while (listElement.firstChild) {
            listElement.removeChild(listElement.lastChild);
        }
    }

    static clearActiveSelectableItem(listElement) {
        listElement.querySelectorAll('li.active')
            .forEach(element => element.classList.remove('active'));
    }
}

class SportComponent extends ConfigItemComponent {
    static $hook = document.getElementById('sport-list');

    static $url = '/config/sports';
    static $prefix = 's-';
    static $template = `
      <li class="selectable">
        <div class="columns is-mobile is-align-items-center">
          <span class="column is-5 ${SportComponent.$prefix}-name"></span>
          <div class="column is-5">
            <input class="${SportComponent.$prefix}-trigger-time" type="number"
              aria-label="Sport trigger time" placeholder="Trigger time"
              min="10" step="5">
          </div>
          <div class="column is-2 is-flex">
            <input class="${SportComponent.$prefix}-is-enabled" type="checkbox" aria-label="Enable sport">          
          </div>
        </div>
      </li>
    `;

    constructor(data) {
        super(data, SportComponent.$template, SportComponent.$prefix);
        this._initializeListeners();
    }

    _initializeListeners() {
        super._initializeListeners(SportComponent.$url);

        this._nameSlot.addEventListener('click', async event => {
            event.preventDefault();

            let response;
            try {
                response = await axios.get(MarketComponent.$url, {
                    params: {
                        sport_id: this.data.id
                    }
                });
            } catch (e) {
                console.error('While fetching markets:', e);
                return;
            }

            ConfigItemComponent.clearConfigItemList(MarketComponent.$hook);
            ConfigItemComponent.clearConfigItemList(BetComponent.$hook);

            ConfigItemComponent.clearActiveSelectableItem(SportComponent.$hook);
            this.root.classList.add('active');

            response.data.markets.forEach(marketData => {
                const market = new MarketComponent(marketData);
                MarketComponent.$hook.appendChild(market.root);
            });

            MarketComponent.$hook.scrollIntoView({
                block: 'start',
                behavior: 'smooth'
            });
        });
    }

    static async getAllSports() {
        let response;
        try {
            response = await axios.get(SportComponent.$url);
        } catch (e) {
            console.error('While fetching sports:', e);
            return;
        }

        ConfigItemComponent.clearConfigItemList(SportComponent.$hook);

        response.data.sports.forEach(sportData => {
            const sport = new SportComponent(sportData);
            SportComponent.$hook.appendChild(sport.root);
        });
    }
}

class MarketComponent extends ConfigItemComponent {
    static $hook = document.getElementById('market-list');

    static $url = '/config/markets';
    static $prefix = 'm-';
    static $template = `
      <li class="selectable">
        <div class="columns is-mobile is-align-items-center">
          <span class="column is-5 ${MarketComponent.$prefix}-name"></span>
          <div class="column is-5">
            <input class="${MarketComponent.$prefix}-trigger-time" type="number"
              aria-label="Market trigger time" placeholder="Trigger time"
              min="10" step="5">
          </div>
          <div class="column is-2 is-flex">
            <input class="${MarketComponent.$prefix}-is-enabled" type="checkbox" aria-label="Enable market">          
          </div>
        </div>
      </li>
    `;

    constructor(data) {
        super(data, MarketComponent.$template, MarketComponent.$prefix);
        this._initializeListeners();
    }

    _initializeListeners() {
        super._initializeListeners(MarketComponent.$url);
        this._initializeTriggerTimeInputClickListeners(MarketComponent.$url);

        this._nameSlot.addEventListener('click', async event => {
            event.preventDefault();

            let response;
            try {
                response = await axios.get(BetComponent.$url, {
                    params: {
                        sport_id: this.data.sport_id,
                        market_id: this.data.id
                    }
                });
            } catch (e) {
                console.error('While fetching bets:', e);
                return;
            }

            ConfigItemComponent.clearConfigItemList(BetComponent.$hook);

            ConfigItemComponent.clearActiveSelectableItem(MarketComponent.$hook);
            this.root.classList.add('active');

            response.data.bets.forEach(betData => {
                const bet = new BetComponent(betData);
                BetComponent.$hook.appendChild(bet.root);
            });

            BetComponent.$hook.scrollIntoView({
                block: 'start',
                behavior: 'smooth'
            });
        });
    }
}

class BetComponent extends ConfigItemComponent {
    static $hook = document.getElementById('bet-list');

    static $url = '/config/bets';
    static $prefix = 'b-';
    static $template = `
      <li>
        <div class="columns is-mobile is-align-items-center">
          <span class="column is-10 ${BetComponent.$prefix}-name"></span>
          <div class="column is-2 is-flex">
            <input class="${BetComponent.$prefix}-is-enabled" type="checkbox" aria-label="Enable bet">          
          </div>
        </div>
      </li>
    `;

    constructor(data) {
        super(data, BetComponent.$template, BetComponent.$prefix);
        this._initializeListeners();
    }

    _initializeListeners() {
        super._initializeListeners(BetComponent.$url);
    }
}


document.querySelectorAll('.config-navigator').forEach(element => {
    element.addEventListener('click', event => {
        event.preventDefault();

        const target = document.getElementById(element.dataset.target);
        target.scrollIntoView({
            'block': 'start',
            'behavior': 'smooth'
        });
    });
});

document.addEventListener('readystatechange', async () => {
    await SportComponent.getAllSports();
});
