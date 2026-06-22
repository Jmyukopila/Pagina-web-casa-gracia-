"""Embedded hotel assistant: stateless FAQ + info + escalation chatbot.

Ported from the standalone C:\\chatbot project and adapted to run inside the
Casa Gracia web app as a same-origin endpoint. It is STATELESS on the server
(conversation history travels with each request from the browser), so it works
on serverless (Vercel) without a database.
"""
