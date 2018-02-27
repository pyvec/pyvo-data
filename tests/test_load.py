from pathlib import Path

data_dir = Path(__file__).parent.parent


def test_at_least_one_event_present():
    # This loads the DB, making sure it *can* be loaded
    from pyvodb.load import get_db
    from pyvodb.tables import Event
    db = get_db(str(data_dir))
    cnt = db.query(Event).count()
    print(cnt)
    if not cnt:
        exit("no events found")
