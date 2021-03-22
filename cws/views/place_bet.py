from collections import OrderedDict

from flask import Blueprint, render_template, current_app, request
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from cws.bots.bet_bot import BetBot, BotInvalidCredentialsError
from cws.models import BettingBot
from cws.redis_manager import RedisManager

bp = Blueprint('place_bet', __name__, url_prefix='/place_bet')

# noinspection PyTypeHints
current_app.session: Session

# noinspection PyTypeHints
current_app.redis_manager: RedisManager


@bp.route('/')
def main():
    db_error = False

    bots = []
    try:
        bots = current_app.session.query(BettingBot).order_by(
            BettingBot.category_id.asc(), BettingBot.name.asc()
        ).all()

    except SQLAlchemyError:
        db_error = True
        current_app.session.rollback()
    finally:
        current_app.session.close()

    if db_error:
        return '', 500

    grouped_bots = OrderedDict()
    for bot in bots:
        bot: BettingBot

        bot.wallet_balance = current_app.redis_manager.get_bet_bot_wallet_balance(bot.id)

        category_name = bot.category.name if bot.category_id is not None else 'Uncategorized'
        bot_group = grouped_bots.setdefault(category_name, [])
        bot_group.append(bot)

    return render_template('place_bet.html', bots=grouped_bots)


@bp.route('/place', methods=('POST',))
def place_bet():
    try:
        bot_ids = [int(bot_id) for bot_id in request.json['bot_ids']]
        selection_id = request.json['selection_id']
        stake = float(request.json['stake'])
        odds = float(request.json['odds'])
    except (TypeError, KeyError, ValueError):
        return '', 400

    db_error = False

    # Get bot data from database
    bots_db = []
    try:
        bots_db = current_app.session.query(BettingBot).filter(BettingBot.id.in_(bot_ids)).all()
    except SQLAlchemyError:
        db_error = True
        current_app.session.rollback()
    finally:
        current_app.session.close()

    if db_error or len(bots_db) != len(bot_ids):
        return '', 500

    # Construct bots and load session data
    results = []
    bots = {}
    for bot_data in bots_db:
        bot_data: BettingBot

        bot = BetBot(bot_data.username, bot_data.password,
                     bot_data.bookmaker, bot_data.proxy_country_code,
                     bot_data.is_enabled, log_in=False)

        session_data = current_app.redis_manager.get_bot_session_data(bot_data.id)
        if session_data is None:
            try:
                bot.login(get_sportsbook_token=True)
            except BotInvalidCredentialsError:
                results.append({'id': bot_data.id, 'result': 'Incorrect credentials'})
            except Exception as e:
                results.append({'id': bot_data.id, 'result': f'{type(e)} - {str(e)}'})
            else:
                bots[bot_data.id] = bot
        else:
            bot.load_session_data(session_data)
            bots[bot_data.id] = bot

    # Place bets and get results
    for bot_id, bot in bots.items():
        try:
            result = bot.place_bet(stake, odds, selection_id)
        except Exception as e:
            result = str(e)

        results.append({
            'id': bot_id,
            'result': result
        })

    for bot_id, bot in bots.items():
        # noinspection PyBroadException
        try:
            wallet = bot.get_wallet_balance(reload=True)
            current_app.redis_manager.set_bet_bots_wallet_balance(bot_id, wallet)
        except:
            pass

    return {'results': results}
