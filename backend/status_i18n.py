"""Translations for the server-rendered status page.

The dashboard is a Nuxt SPA with @nuxtjs/i18n, but /status is plain Flask +
Jinja on purpose: it has to stay readable when the SPA bundle or the database
is broken. So it carries its own small catalogue rather than pulling in the
frontend's.

The active locale comes from the same cookie @nuxtjs/i18n writes, falling back
to Accept-Language, so switching language in the app also switches this page.
"""

COOKIE = "wikibias_locale"
DEFAULT = "fr"
SUPPORTED = ("fr", "en")

STRINGS = {
    "fr": {
        "title": "File d'analyse — WikiBias Analyzer",
        "heading": "File d'analyse",
        "refresh": "Cette page se rafraîchit toutes les 15 secondes.",
        "backToTool": "Retour à l'outil",
        "json": "JSON",
        "syncMode": "mode synchrone",
        "dbDown": "Base de données injoignable :",
        "total": "total",
        "pending": "en attente",
        "running": "en cours",
        "done": "terminé",
        "error": "échec",
        "activeHeading": "{n} analyse(s) en cours ou en attente",
        "colArticle": "Article",
        "colStatus": "Statut",
        "colProgress": "Avancement",
        "colDuration": "Durée",
        "colSources": "Sources",
        "colAttempts": "Essais",
        "colError": "Erreur",
        "colUpdated": "Mis à jour",
        "empty": "Aucune analyse enregistrée pour le moment.",
        "finished": "✓ Analyse terminée",
        "sourcesAnalysed": "{n} source(s) analysée(s)",
        "failed": "✕ Échec",
        "attemptsMade": "{n} tentative(s)",
        "permanentFailure": "définitif — inutile de réessayer",
        "waitingForWorker": "en attente d'un worker",
        "extracting": "extraction des références…",
        "noProgressSince": "aucune progression depuis {quiet}",
        "remaining": "reste",
        "stageSources": "analyse des sources",
        "stageAggregating": "agrégation des résultats",
        "durRunning": "en cours depuis",
        "durPending": "en attente depuis",
        "durTotal": "durée totale",
        "underMinute": "moins d'une minute",
        "auditTitle": "Auto-contrôle — WikiBias Analyzer",
        "auditHeading": "Auto-contrôle",
        "auditIntro": "Contrôles réfutables sur nos propres résultats, exécutés sur les analyses réellement stockées. Un outil qui ne publie que ses résultats demande qu'on lui fasse confiance ; publier aussi ses échecs le rend critiquable.",
        "auditReference": "Table de référence",
        "auditClean": "analyses passant tous les contrôles",
        "auditChecks": "Contrôles",
        "auditCheck": "Contrôle",
        "auditWhat": "Ce qui est vérifié",
        "auditResult": "Résultat",
        "auditPassing": "✓ passe",
        "auditFailing": "✕ {n} échec(s)",
        "auditPerAnalysis": "Par analyse",
        "auditRevision": "Révision",
        "auditMethod": "Méthode",
    },
    "en": {
        "title": "Analysis queue — WikiBias Analyzer",
        "heading": "Analysis queue",
        "refresh": "This page refreshes every 15 seconds.",
        "backToTool": "Back to the tool",
        "json": "JSON",
        "syncMode": "synchronous mode",
        "dbDown": "Database unreachable:",
        "total": "total",
        "pending": "queued",
        "running": "running",
        "done": "done",
        "error": "failed",
        "activeHeading": "{n} analysis(es) running or queued",
        "colArticle": "Article",
        "colStatus": "Status",
        "colProgress": "Progress",
        "colDuration": "Duration",
        "colSources": "Sources",
        "colAttempts": "Attempts",
        "colError": "Error",
        "colUpdated": "Updated",
        "empty": "No analyses recorded yet.",
        "finished": "✓ Analysis complete",
        "sourcesAnalysed": "{n} source(s) analysed",
        "failed": "✕ Failed",
        "attemptsMade": "{n} attempt(s)",
        "permanentFailure": "permanent — retrying will not help",
        "waitingForWorker": "waiting for a worker",
        "extracting": "extracting references…",
        "noProgressSince": "no progress for {quiet}",
        "remaining": "remaining",
        "stageSources": "analysing sources",
        "stageAggregating": "aggregating results",
        "durRunning": "running for",
        "durPending": "queued for",
        "durTotal": "total duration",
        "underMinute": "less than a minute",
        "auditTitle": "Self-check — WikiBias Analyzer",
        "auditHeading": "Self-check",
        "auditIntro": "Falsifiable checks on our own output, run against the analyses actually stored. A tool that publishes only its results asks to be trusted; publishing its failures too makes it criticisable.",
        "auditReference": "Reference tables",
        "auditClean": "analyses passing every check",
        "auditChecks": "Checks",
        "auditCheck": "Check",
        "auditWhat": "What is verified",
        "auditResult": "Result",
        "auditPassing": "✓ passing",
        "auditFailing": "✕ {n} failure(s)",
        "auditPerAnalysis": "Per analysis",
        "auditRevision": "Revision",
        "auditMethod": "Method",
    },
}


def pick_locale(request):
    """Cookie first (an explicit choice), then Accept-Language."""
    cookie = (request.cookies.get(COOKIE) or "").strip().lower()
    if cookie in SUPPORTED:
        return cookie
    accepted = request.accept_languages.best_match(SUPPORTED)
    return accepted or DEFAULT


def translator(locale):
    table = STRINGS.get(locale, STRINGS[DEFAULT])
    fallback = STRINGS[DEFAULT]

    def t(key, **params):
        text = table.get(key, fallback.get(key, key))
        return text.format(**params) if params else text

    return t
