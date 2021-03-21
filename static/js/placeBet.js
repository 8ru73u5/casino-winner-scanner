function saveBetDataToLocalStorage({eventName, betName, tipName, odds, selectionId}) {
    window.localStorage.setItem('betData', JSON.stringify({
        eventName,
        betName,
        tipName,
        odds,
        selectionId
    }));
}

function getBetDataFromLocalStorage() {
    const betData = window.localStorage.getItem('betData');

    if (betData !== null) {
        return JSON.parse(betData);
    } else {
        return null;
    }
}

function updateBetSummary() {
    const betData = getBetDataFromLocalStorage();
    const empty = '―';

    document.getElementById('auto-event-name').innerText = betData?.eventName ?? empty;
    document.getElementById('auto-bet-name').innerText = betData?.betName ?? empty;
    document.getElementById('auto-tip-name').innerText = betData?.tipName ?? empty;
    document.getElementById('auto-odds').innerText = betData?.odds ?? empty;
}

function disableUnselectedBetDataProvider() {
    const selected = document.querySelector('input[name="details-provider"]:checked');
    const unselected = document.querySelector('input[name="details-provider"]:not(:checked)');

    selected.closest('.column').querySelector('fieldset').removeAttribute('disabled');
    unselected.closest('.column').querySelector('fieldset').setAttribute('disabled', '');
}

function placeBet() {
    const bots = Array.from(document.querySelectorAll('input.bot-item:checked'))
        .map(botItem => {
            return {
                id: parseInt(botItem.value),
                name: botItem.parentElement.innerText.trim()
            };
        });

    if (bots.length === 0) {
        swal('No bot specified', 'Please choose at least one bot from the list', 'error');
        return;
    }

    const detailsProvider = document.querySelector('input[name="details-provider"]:checked').value;
    const betData = getBetDataFromLocalStorage();
    let selectionId = null;
    let odds = null;

    if (detailsProvider === 'auto') {
        if (betData == null) {
            swal('Missing bet data', 'Go back to the dashboard and click desired tip', 'error');
            return;
        }

        selectionId = betData.selectionId;
        odds = betData.odds;

        if (selectionId == null || odds == null) {
            swal('Invalid bet data', 'Contact developer to fix this', 'error');
            return;
        }
    } else {
        selectionId = document.getElementById('manual-selection-id').value;
        odds = document.getElementById('manual-odds').value;

        if (selectionId.length === 0 || odds.length === 0) {
            swal('Missing bet data', 'Please fill in "Selection ID" and "Odds" fields', 'error');
            return;
        }
    }

    const stake = document.getElementById('stake').value;

    if (stake.length === 0) {
        swal('Missing stake', 'Please specify the stake', 'error');
        return;
    }

    let betDataSummary;
    if (detailsProvider === 'auto') {
        betDataSummary = `Event: ${betData.eventName}\nBet: ${betData.betName}\nTip: ${betData.tipName} (${betData.odds})`;
    } else {
        betDataSummary = `Selection ID: ${selectionId}\nOdds: ${odds}`;
    }

    const botSummary = bots.reduce((summary, {name}) => {
        summary += `\n- ${name}`;
        return summary;
    }, '');

    swal({
        title: 'Bet summary',
        text: `${betDataSummary}\n\nBots:${botSummary}\n\nStake: ${stake}`,
        icon: 'warning',
        buttons: ['Cancel', 'Confirm'],
        dangerMode: true
    }).then(value => {
        if (value) {
            swal('Success!', 'Bet was successfully placed!', 'success');
        }
    });
}
