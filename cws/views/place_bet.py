from collections import OrderedDict

from flask import Blueprint, render_template, current_app
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from cws.models import BettingBot

bp = Blueprint('place_bet', __name__, url_prefix='/place_bet')

# noinspection PyTypeHints
current_app.session: Session


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
        category_name = bot.category.name if bot.category_id is not None else 'Uncategorized'
        bot_group = grouped_bots.setdefault(category_name, [])
        bot_group.append(bot)

    return render_template('place_bet.html', bots=grouped_bots)
