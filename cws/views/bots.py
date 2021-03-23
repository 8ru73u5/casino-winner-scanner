from flask import Blueprint, render_template, request, current_app, redirect, url_for, flash
from sqlalchemy import and_
from sqlalchemy.exc import SQLAlchemyError

from cws.bots.bet_bot import BookmakerType, BetBot, BotInvalidCredentialsError
from cws.models import BettingBot, BettingBotHistory, BettingBotCategory
from cws.views.auth import login_required

bp = Blueprint('bots', __name__, url_prefix='/bots')

_proxy_countries = {
    'US': 'United States',
    'DE': 'Germany',
    'BR': 'Brazil',
    'ES': 'Spain',
    'PL': 'Poland'
}


@bp.route('/')
@login_required
def overview():
    db_error = False
    bots = []
    categories = []

    try:
        bots = current_app.session.query(BettingBot).all()
        categories = current_app.session.query(BettingBotCategory).all()
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

    return render_template('bots/overview.html', bots=bots, proxies=_proxy_countries, categories=categories)


@bp.route('/add', methods=('GET', 'POST'))
@login_required
def add_bot():
    if request.method == 'GET':
        db_error = False
        categories = []

        try:
            categories = current_app.session.query(BettingBotCategory).all()
        except SQLAlchemyError:
            db_error = True
        finally:
            current_app.session.close()

        if db_error:
            return '', 500
        else:
            return render_template('bots/add_bot.html', proxies=_proxy_countries, categories=categories)

    try:
        bot_name = request.form['bot_name']
        bot_category_id = int(category) if (category := request.form['bot_category']) != '' else None
        username = request.form['username']
        password = request.form['password']
        bookmaker = request.form['bookmaker']
        country_code = request.form['country_code']
    except (KeyError, ValueError):
        return '', 400

    if bookmaker == 'BETSSON':
        bookmaker = BookmakerType.BETSSON
    elif bookmaker == 'BETSAFE':
        bookmaker = BookmakerType.BETSAFE
    else:
        return '', 400

    db_error = False
    bot_already_exists_error = False
    bot_name_already_exists_error = False
    invalid_category_error = False
    bot_invalid_credentials_error = False

    try:
        existing_bot_query = current_app.session.query(BettingBot).filter(and_(
            BettingBot.username == username,
            BettingBot.bookmaker == bookmaker
        ))

        existing_name_query = current_app.session.query(BettingBot).filter(
            BettingBot.name == bot_name
        )

        category_query = current_app.session.query(BettingBotCategory).filter(
            BettingBotCategory.id == bot_category_id
        )

        bot_exists = current_app.session.query(existing_bot_query.exists()).scalar()
        bot_name_exists = current_app.session.query(existing_name_query.exists()).scalar()

        if bot_category_id is not None:
            category_exists = current_app.session.query(category_query.exists()).scalar()
        else:
            category_exists = True

        if bot_exists:
            bot_already_exists_error = True
        elif bot_name_exists:
            bot_name_already_exists_error = True
        elif not category_exists:
            invalid_category_error = True
        else:
            try:
                bot_login = BetBot(username, password, bookmaker, country_code, is_enabled=True)
                bot_login.login()
            except BotInvalidCredentialsError:
                bot_invalid_credentials_error = True
            else:
                bot_login.logout()

                bot = BettingBot(
                    name=bot_name, category_id=bot_category_id,
                    username=username, password=password,
                    bookmaker=bookmaker, proxy_country_code=country_code
                )
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
        flash(f'Email: {username} already exists for {bookmaker.name} bookmaker', 'bot--credentials')
    elif bot_name_already_exists_error:
        flash(f'Name: {bot_name} is already taken', 'bot--name')
    elif invalid_category_error:
        return '', 400
    elif bot_invalid_credentials_error:
        flash('Provided credentials are invalid', 'bot--credentials')
    else:
        return redirect(url_for('bots.overview'))

    return redirect(url_for('bots.add_bot'))


@bp.route('/bot/<int:bot_id>')
@login_required
def bot_history(bot_id):
    db_error = False
    not_found_error = False

    history = []
    try:
        bot = current_app.session.query(BettingBot).get(bot_id)

        if bot is None:
            not_found_error = True
        else:
            history = current_app.session.query(BettingBotHistory) \
                .filter(BettingBotHistory.bot_id == bot_id) \
                .order_by(BettingBotHistory.id.desc()) \
                .limit(50).all()
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
        return render_template('bots/history.html', bet_history=history)


@bp.route('/bot/<int:bot_id>/bookmaker')
@login_required
def bot_bookmaker_history(bot_id):
    bet_history = current_app.redis_manager.get_bet_bot_bet_history(bot_id)

    if bet_history is None:
        bet_history = []

    return render_template('bots/bookmaker_history.html', bet_history=bet_history)


@bp.route('/bot/<int:bot_id>', methods=('PATCH',))
@login_required
def manage_bot(bot_id):
    try:
        is_enabled = request.json['is_enabled']
        category_id = int(category) if (category := request.json['category_id']) != '' else None
        country_code = request.json['country_code']
    except (KeyError, ValueError):
        return '', 400

    if not isinstance(is_enabled, bool):
        return '', 400

    db_error = False
    not_found_error = False
    invalid_category_error = False

    try:
        bot = current_app.session.query(BettingBot).get(bot_id)
        category = current_app.session.query(BettingBotCategory).get(category_id)

        if bot is None:
            not_found_error = True
        elif category is None and category_id is not None:
            invalid_category_error = True
        else:
            bot.is_enabled = is_enabled
            bot.category_id = category_id
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
    elif invalid_category_error:
        return '', 400
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


@bp.route('/add_category', methods=('POST',))
@login_required
def add_category():
    try:
        category_name = request.form['category_name']
    except KeyError:
        return '', 400

    db_error = False
    category_exists = False

    try:
        existing_category = current_app.session.query(BettingBotCategory).filter(
            BettingBotCategory.name == category_name
        ).first()

        if existing_category is not None:
            category_exists = True
        else:
            current_app.session.add(BettingBotCategory(name=category_name))
            current_app.session.commit()
    except SQLAlchemyError:
        db_error = True
        current_app.session.rollback()
    finally:
        current_app.session.close()

    if db_error:
        return '', 500
    elif category_exists:
        flash(f'Category name: {category_name} is already taken', 'category_add--name')

    return redirect(url_for('bots.add_bot'))


@bp.route('/modify_category', methods=('POST',))
@login_required
def modify_category():
    try:
        category_id = int(request.form['category_id'])
        category_name = request.form['category_name']
    except (KeyError, ValueError):
        return '', 400

    db_error = False
    invalid_category_error = False
    name_already_taken_error = False

    try:
        existing_category = current_app.session.query(BettingBotCategory).get(category_id)

        category_with_the_same_name = current_app.session.query(BettingBotCategory).filter(
            BettingBotCategory.name == category_name
        ).first()

        if existing_category is None:
            invalid_category_error = True
        elif category_with_the_same_name is not None:
            name_already_taken_error = True
        else:
            existing_category.name = category_name
            current_app.session.commit()
    except SQLAlchemyError:
        db_error = True
        current_app.session.rollback()
    finally:
        current_app.session.close()

    if db_error:
        return '', 500
    elif invalid_category_error:
        return '', 400
    elif name_already_taken_error:
        flash(f'Category {category_name} is already taken', 'category_mod--name')

    return redirect(url_for('bots.add_bot'))


@bp.route('/delete_category', methods=('POST',))
@login_required
def delete_category():
    try:
        category_id = int(request.form['category_id'])
    except (KeyError, ValueError):
        return '', 400

    db_error = False
    category_not_found_error = False

    try:
        category_to_remove = current_app.session.query(BettingBotCategory).get(category_id)

        if category_to_remove is None:
            category_not_found_error = True
        else:
            current_app.session.delete(category_to_remove)
            current_app.session.commit()
    except SQLAlchemyError:
        db_error = True
        current_app.session.rollback()
    finally:
        current_app.session.close()

    if db_error:
        return '', 500
    elif category_not_found_error:
        return '', 404
    else:
        return redirect(url_for('bots.add_bot'))
