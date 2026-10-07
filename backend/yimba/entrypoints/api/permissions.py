"""Permission codes required by the routes (defined by the identity module, listed in ``appdesc.yml``)."""

from yimba.modules.identity.public import Permission

WATCH_CREATE = Permission.WATCH_CREATE
WATCH_READ = Permission.WATCH_READ
WATCH_UPDATE = Permission.WATCH_UPDATE
WATCH_DELETE = Permission.WATCH_DELETE
MENTION_READ = Permission.MENTION_READ
STATISTICS_READ = Permission.STATISTICS_READ
ALERT_READ = Permission.ALERT_READ
ALERT_ACKNOWLEDGE = Permission.ALERT_ACKNOWLEDGE
USER_READ = Permission.USER_READ
USER_MANAGE = Permission.USER_MANAGE
