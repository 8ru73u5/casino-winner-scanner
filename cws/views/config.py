from flask import Blueprint, render_template, current_app, request
from sqlalchemy import and_
from sqlalchemy.exc import SQLAlchemyError

from cws.models import Sport, Market, Bet

bp = Blueprint('config', __name__, url_prefix='/config')


@bp.route('/')
def main():
    return render_template('config.html')


@bp.route('/sports')
def get_sports():
    db_error = False
    sports = []

    try:
        sports = [sport.to_json() for sport in current_app.session.query(Sport).all()]
    except SQLAlchemyError:
        db_error = True
        current_app.session.rollback()
    finally:
        current_app.session.close()

    if db_error:
        return '', 500
    else:
        return {'sports': sports}


@bp.route('/markets')
def get_markets():
    try:
        sport_id = int(request.args['sport_id'])
    except (KeyError, ValueError):
        return '', 400

    db_error = False
    markets = []

    try:
        markets = [
            market.to_json()
            for market in current_app.session.query(Market).filter(Market.sport_id == sport_id).all()
        ]
    except SQLAlchemyError:
        db_error = True
        current_app.session.rollback()
    finally:
        current_app.session.close()

    if db_error:
        return '', 500
    else:
        return {'markets': markets}


@bp.route('/bets')
def get_bets():
    try:
        sport_id = int(request.args['sport_id'])
        market_id = int(request.args['market_id'])
    except (KeyError, ValueError):
        return '', 400

    db_error = False
    bets = []

    try:
        bets = [
            bet.to_json()
            for bet in current_app.session.query(Bet).filter(and_(
                Bet.sport_id == sport_id, Bet.market_id == market_id
            )).all()
        ]
    except SQLAlchemyError:
        db_error = True
        current_app.session.rollback()
    finally:
        current_app.session.close()

    if db_error:
        return '', 500
    else:
        return {'bets': bets}


@bp.route('/sports', methods=('PATCH',))
def set_sport_data():
    try:
        sport_id = int(request.json['sport_id'])
        is_enabled = request.json['is_enabled']
        trigger_time = int(request.json['trigger_time'])
    except (KeyError, ValueError):
        return '', 400

    if not isinstance(is_enabled, bool):
        return '', 400

    db_error = False
    not_found_error = False

    try:
        existing_sport = current_app.session.query(Sport).get(sport_id)

        if existing_sport is None:
            not_found_error = True
        else:
            existing_sport.is_enabled = is_enabled
            existing_sport.trigger_time = trigger_time
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


@bp.route('/markets', methods=('PATCH',))
def set_market_data():
    try:
        sport_id = int(request.json['sport_id'])
        market_id = int(request.json['market_id'])
        is_enabled = request.json['is_enabled']
        trigger_time = request.json['trigger_time']
    except (KeyError, ValueError):
        return '', 400

    if not isinstance(is_enabled, bool):
        return '', 400

    if trigger_time is not None:
        try:
            trigger_time = int(trigger_time)
        except ValueError:
            return '', 400

    db_error = False
    not_found_error = False

    try:
        existing_market = current_app.session.query(Market).get({
            'id': market_id, 'sport_id': sport_id
        })

        if existing_market is None:
            not_found_error = True
        else:
            existing_market.is_enabled = is_enabled
            existing_market.trigger_time = trigger_time
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


@bp.route('/bets', methods=('PATCH',))
def set_bet_data():
    try:
        sport_id = int(request.json['sport_id'])
        market_id = int(request.json['market_id'])
        bet_id = int(request.json['bet_id'])
        is_enabled = request.json['is_enabled']
    except (KeyError, ValueError):
        return '', 400

    if not isinstance(is_enabled, bool):
        return '', 400

    db_error = False
    not_found_error = False

    try:
        existing_bet = current_app.session.query(Bet).get({
            'id': bet_id, 'sport_id': sport_id, 'market_id': market_id
        })

        if existing_bet is None:
            not_found_error = True
        else:
            existing_bet.is_enabled = is_enabled
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
