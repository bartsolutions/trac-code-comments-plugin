# -*- coding: utf-8 -*-

from trac.core import Component, implements
from trac.ticket.api import ITicketChangeListener

import re

from code_comments.comment_macro import CodeCommentLinkMacro


class UpdateTicketCodeComments(Component):
    """Automatically stores relations to CodeComments whenever a ticket
    is saved or created
    Note: This does not catch edits on replies right away but on the next
    change of the ticket or when adding a new reply
    """

    implements(ITicketChangeListener)

    def ticket_created(self, ticket):
        self.update_relations(ticket)

    def ticket_changed(self, ticket, comment, author, old_values):
        self.update_relations(ticket)

    def ticket_deleted(self, ticket):
        self.update_relations(ticket)

    def update_relations(self, ticket):
        comment_ids = []
        # (time, author, field, oldvalue, newvalue, permanent)
        changes = ticket.get_changelog()
        description = ticket['description']

        comment_ids += re.findall(CodeCommentLinkMacro.re, description)
        if changes:
            for change in changes:
                if change[2] == 'comment':
                    comment_ids += re.findall(CodeCommentLinkMacro.re,
                                              change[4])

        comment_ids = set(comment_ids)
        comment_ids_csv = ','.join(comment_ids)

        existing_comments_query = """
            SELECT * FROM ticket_custom
            WHERE ticket=%s AND name = 'code_comment_relation'
        """
        existing_comments = self.fetch(existing_comments_query, [ticket.id])

        if existing_comments:
            self.query("""
                UPDATE ticket_custom SET value=%s
                WHERE ticket=%s AND name='code_comment_relation'
                """, (comment_ids_csv, ticket.id))
        else:
            self.query("""
                INSERT INTO ticket_custom (ticket, name, value)
                VALUES (%s, 'code_comment_relation', %s)
                """, (ticket.id, comment_ids_csv))

    def query(self, query, args=[], result_callback=None):
        if result_callback is None:
            def result_callback(db, cursor):
                return True
        result = {}

        @self.env.with_transaction()
        def insert_comment(db):
            cursor = db.cursor()
            cursor.execute(query, args)
            result['result'] = result_callback(db, cursor)
        return result['result']

    def fetch(self, query, args=[]):
        return self.query(query, args, lambda db, cursor: cursor.fetchall())
