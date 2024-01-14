"""
Term status following.
"""

import pytest

from lute.models.term import Term as DBTerm
from lute.db import db
from tests.dbasserts import assert_sql_result


@pytest.fixture(name="term_family")
def fixture_term_family(app_context, english):
    """
    Term family.

    A
      B - follows
        b1 - follows
        b2 - no
      C - does not follow
        c1 - follows
        c2 - no
    """

    class family:
        "Family of terms."

        def __init__(self):
            "Set up terms."
            # pylint: disable=invalid-name
            A = DBTerm(english, "A")
            B = DBTerm(english, "Byes")
            B.add_parent(A)
            B.follow_parent = True
            b1 = DBTerm(english, "b1yes")
            b1.add_parent(B)
            b1.follow_parent = True
            b2 = DBTerm(english, "b2no")
            b2.add_parent(B)

            C = DBTerm(english, "Cno")
            C.add_parent(A)
            c1 = DBTerm(english, "c1yes")
            c1.add_parent(C)
            c1.follow_parent = True
            c2 = DBTerm(english, "c2no")
            c2.add_parent(C)

            db.session.add(A)
            db.session.add(B)
            db.session.add(b1)
            db.session.add(b2)
            db.session.add(C)
            db.session.add(c1)
            db.session.add(c2)
            db.session.commit()

            self.A = A
            self.B = B
            self.b1 = b1
            self.b2 = b2
            self.C = C
            self.c1 = c1
            self.c2 = c2

    f = family()

    expected_initial_state = """
    A: 1
    Byes: 1
    b/1/yes: 1
    b/2/no: 1
    Cno: 1
    c/1/yes: 1
    c/2/no: 1
    """
    assert_statuses(expected_initial_state, "initial state")

    return f


def assert_statuses(expected, msg):
    "Check the statuses of terms."
    lines = [
        s.strip().replace(":", ";") for s in expected.split("\n") if s.strip() != ""
    ]
    sql = "select WoText, WoStatus from words order by WoTextLC"
    assert_sql_result(sql, lines, msg)


def test_parent_status_propagates_down(term_family, app_context):
    "Changing status should propagate down the tree."
    f = term_family
    f.A.status = 4
    db.session.add(f.A)
    db.session.commit()

    expected = """
    A: 4
    Byes: 4
    b/1/yes: 4
    b/2/no: 1
    Cno: 1
    c/1/yes: 1
    c/2/no: 1
    """
    assert_statuses(expected, "updated")


def test_term_propagates_up_and_down(term_family, app_context):
    "Parent and child also updated."
    f = term_family
    f.B.status = 4
    db.session.add(f.B)
    db.session.commit()

    expected = """
    A: 4
    Byes: 4
    b/1/yes: 4
    b/2/no: 1
    Cno: 1
    c/1/yes: 1
    c/2/no: 1
    """
    assert_statuses(expected, "updated")


def test_term_stops_propagating_to_top(term_family, app_context):
    "Goes up the tree until it stops."
    f = term_family
    f.c1.status = 4
    db.session.add(f.c1)
    db.session.commit()

    expected = """
    A: 1
    Byes: 1
    b/1/yes: 1
    b/2/no: 1
    Cno: 4
    c/1/yes: 4
    c/2/no: 1
    """
    assert_statuses(expected, "updated")


def test_term_not_following_parent(term_family, app_context):
    "Doesn't update parent."
    f = term_family
    f.b2.status = 4
    db.session.add(f.b2)
    db.session.commit()

    expected = """
    A: 1
    Byes: 1
    b/1/yes: 1
    b/2/no: 4
    Cno: 1
    c/1/yes: 1
    c/2/no: 1
    """
    assert_statuses(expected, "updated")


def test_parent_not_updated_if_term_has_multiple_parents(term_family, app_context):
    "Doesn't update parent."
    f = term_family
    f.c1.add_parent(f.B)
    db.session.add(f.c1)
    db.session.commit()

    f.c1.status = 4
    db.session.add(f.c1)
    db.session.commit()

    expected = """
    A: 1
    Byes: 1
    b/1/yes: 1
    b/2/no: 1
    Cno: 1
    c/1/yes: 4
    c/2/no: 1
    """
    assert_statuses(expected, "updated")


def test_adding_new_term_changes_family_if_added(english, term_family, app_context):
    "Doesn't update parent."
    f = term_family

    b3 = DBTerm(english, "b3yes")
    b3.add_parent(f.B)
    b3.status = 3
    b3.follow_parent = True
    db.session.add(b3)
    db.session.commit()

    expected = """
    A: 3
    Byes: 3
    b/1/yes: 3
    b/2/no: 1
    b/3/yes: 3
    Cno: 1
    c/1/yes: 1
    c/2/no: 1
    """
    assert_statuses(expected, "updated")


def test_adding_new_term_does_not_change_family_if_multiple_parents(
    english, term_family, app_context
):
    "Doesn't update parent."
    f = term_family

    b3 = DBTerm(english, "b3yes")
    b3.parents.append(f.B)
    b3.parents.append(f.C)
    b3.status = 3
    b3.follow_parent = True
    db.session.add(b3)
    db.session.commit()

    expected = """
    A: 1
    Byes: 1
    b/1/yes: 1
    b/2/no: 1
    b/3/yes: 3
    Cno: 1
    c/1/yes: 1
    c/2/no: 1
    """
    assert_statuses(expected, "updated")


# add multiple parents
# changing to follow the parent - updates
