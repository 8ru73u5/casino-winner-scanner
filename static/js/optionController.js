class OptionItemComponent {
    static $url = '/config/option';
    static $optionsInitializers = {
        1: 'option-min-odds',
        2: 'option-max-odds',
        3: 'option-telegram-notification',
        4: 'option-sound-notification',
        5: 'option-telegram-second-notification',
        6: 'option-auto-break-min-idle-time'
    };

    constructor(optionId, optionHookId) {
        this.optionId = optionId;
        this.inputField = document.getElementById(optionHookId);
        this.labelElement = document.querySelector(`label[for="${optionHookId}"]`);
    }

    _getOptionUrl() {
        return `${OptionItemComponent.$url}/${this.optionId}`;
    }

    async _initialize() {
        let response;
        try {
            response = await axios.get(this._getOptionUrl());
        } catch (e) {
            console.error('While fetching option data:', e);
            return;
        }

        const optionData = response.data;
        this.inputField.value = optionData.value;
        this.labelElement.innerHTML = optionData.name;

        this.inputField.addEventListener('change', event => {
            event.preventDefault();
            this._updateOptionData();
        });
    }

    _updateOptionData() {
        axios.patch(this._getOptionUrl(), {
            value: parseFloat(this.inputField.value)
        }).catch(e => console.error('While updating option data:', e));
    }

    static async getAllOptions() {
        for (const [optionId, optionHookId] of Object.entries(OptionItemComponent.$optionsInitializers)) {
            const o = new OptionItemComponent(optionId, optionHookId);
            await o._initialize();
        }
    }
}
