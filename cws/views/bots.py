from flask import Blueprint, render_template, request, current_app, redirect, url_for, flash
from sqlalchemy import and_
from sqlalchemy.exc import SQLAlchemyError

from cws.bots.bet_bot import BookmakerType, BetBot, BotInvalidCredentialsError
from cws.models import BettingBot
from cws.views.auth import login_required

bp = Blueprint('bots', __name__, url_prefix='/bots')

_proxy_countries = {
    'US': 'United States',
    'DE': 'Germany',
    'BR': 'Brazil',
    'ES': 'Spain'
}


@bp.route('/')
@login_required
def overview():
    db_error = False
    bots = []

    try:
        bots = current_app.session.query(BettingBot).all()
    except SQLAlchemyError:
        db_error = True
        current_app.session.rollback()
    finally:
        current_app.session.close()

    if db_error:
        return '', 500

    for bot in bots:
        wb = current_app.redis_manager.get_bet_bot_wallet_balance(bot.id)

        if wb is not None:
            bot.wallet_balance = wb

    return render_template('bots/overview.html', bots=bots, proxies=_proxy_countries)


@bp.route('/add', methods=('GET', 'POST'))
@login_required
def add_bot():
    if request.method == 'GET':
        return render_template('bots/add_bot.html', proxies=_proxy_countries)

    try:
        username = request.form['username']
        password = request.form['password']
        bookmaker = request.form['bookmaker']
        country_code = request.form['country_code']
    except KeyError:
        return '', 400

    if bookmaker == 'BETSSON':
        bookmaker = BookmakerType.BETSSON
    elif bookmaker == 'BETSAFE':
        bookmaker = BookmakerType.BETSAFE
    else:
        return '', 400

    db_error = False
    bot_already_exists_error = False
    bot_invalid_credentials_error = False

    try:
        existing_bot = current_app.session.query(BettingBot).filter(and_(
            BettingBot.username == username,
            BettingBot.bookmaker == bookmaker
        )).first()

        if existing_bot is not None:
            bot_already_exists_error = True
        else:
            try:
                bot_login = BetBot(username, password, bookmaker, country_code, is_enabled=True)
                bot_login.login()
            except BotInvalidCredentialsError:
                bot_invalid_credentials_error = True
            else:
                bot_login.logout()

                bot = BettingBot(username=username, password=password, bookmaker=bookmaker, proxy_country_code=country_code)
                current_app.session.add(bot)
                current_app.session.commit()
    except SQLAlchemyError:
        db_error = True
        current_app.session.rollback()
    finally:
        current_app.session.close()

    if db_error:
        return '', 500
    elif bot_already_exists_error:
        flash(f'Email: {username} already exists for {bookmaker.name} bookmaker')
        return redirect(url_for('bots.add_bot'))
    elif bot_invalid_credentials_error:
        flash('Provided credentials are invalid')
        return redirect(url_for('bots.add_bot'))
    else:
        return redirect(url_for('bots.overview'))


@bp.route('/bot/<int:bot_id>')
@login_required
def bot_history(bot_id):
    return render_template('bots/history.html', bot_id=bot_id)


@bp.route('/bot/<int:bot_id>', methods=('PATCH',))
@login_required
def manage_bot(bot_id):
    try:
        is_enabled = request.json['is_enabled']
        country_code = request.json['country_code']
    except KeyError:
        return '', 400

    if not isinstance(is_enabled, bool):
        return '', 400

    db_error = False
    not_found_error = False

    try:
        bot = current_app.session.query(BettingBot).get(bot_id)

        if bot is None:
            not_found_error = True
        else:
            bot.is_enabled = is_enabled
            bot.proxy_country_code = country_code
            current_app.session.commit()
    except SQLAlchemyError:
        db_error = True
        current_app.session.rollback()
    finally:
        current_app.session.close()

    if db_error:
        return '', 500
    elif not_found_error:
        return '', 404
    else:
        return ''


@bp.route('/bot/<int:bot_id>', methods=('DELETE',))
@login_required
def delete_bot(bot_id):
    db_error = False
    not_found_error = False

    try:
        bot = current_app.session.query(BettingBot).get(bot_id)

        if bot is None:
            not_found_error = True
        else:
            current_app.session.delete(bot)
            current_app.session.commit()
    except SQLAlchemyError:
        db_error = True
        current_app.session.rollback()
    finally:
        current_app.session.close()

    if db_error:
        return '', 500
    elif not_found_error:
        return '', 404
    else:
        return ''
