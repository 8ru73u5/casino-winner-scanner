from flask import Blueprint, render_template, request, current_app
from sqlalchemy.exc import SQLAlchemyError

from cws.bots.bet_bot import BookmakerType
from cws.models import BettingBot
from cws.views.auth import login_required

bp = Blueprint('bots', __name__, url_prefix='/bots')


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

    return render_template('bots/overview.html', bots=bots)


@bp.route('/add')
@login_required
def add_bot_page():
    return render_template('bots/add_bot.html')


@bp.route('/bot', methods=('PUT',))
@login_required
def add_bot():
    try:
        username = request.json['username']
        password = request.json['password']
        bookmaker = request.json['bookmaker']
        country_code = request.json['country_code']
    except KeyError:
        return '', 400

    if bookmaker == 'BETSSON':
        bookmaker = BookmakerType.BETSSON
    elif bookmaker == 'BETSAFE':
        bookmaker = BookmakerType.BETSAFE
    else:
        return '', 400

    db_error = False

    try:
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
    else:
        return ''


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
