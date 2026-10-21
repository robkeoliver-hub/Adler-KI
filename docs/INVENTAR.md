# Routen und Modelle (statisch)
- Zeile 846: `app.route('/')` → `index`
- Zeile 954: `app.route('/demo/jugend')` → `demo_jugend`
- Zeile 959: `app.route('/demo/jugend/ergebnisse')` → `demo_jugend_ergebnisse`
- Zeile 964: `app.route('/demo/jugend/abzeichen')` → `demo_jugend_abzeichen`
- Zeile 969: `app.route('/demo/jugend/termine')` → `demo_jugend_termine`
- Zeile 987: `app.route('/kontakt-downloads')` → `kontakt_downloads`
- Zeile 992: `app.route('/jugend/<token>/kontakt-downloads')` → `jugend_kontakt_downloads`
- Zeile 998: `app.route('/erwachsen/<token>/kontakt-downloads')` → `erwachsen_kontakt_downloads`
- Zeile 1004: `app.route('/jugend/<token>')` → `jugend_start`
- Zeile 1031: `app.post('/jugend/<token>/abzeichen-hinweis/<int:badge_id>/gesehen')` → `jugend_abzeichen_hinweis_gesehen`
- Zeile 1053: `app.route('/jugend/<token>/manifest.webmanifest')` → `jugend_manifest`
- Zeile 1073: `app.route('/service-worker.js')` → `pwa_service_worker`
- Zeile 1082: `app.route('/jugend/<token>/abzeichen')` → `jugend_abzeichen`
- Zeile 1094: `app.route('/jugend/<token>/urkunde/<int:badge_id>')` → `jugend_urkunde`
- Zeile 1105: `app.route('/jugend/<token>/ergebnisse')` → `jugend_ergebnisse`
- Zeile 1119: `app.route('/jugend/<token>/statistik')` → `jugend_statistik`
- Zeile 1124: `app.route('/jugend/<token>/termine')` → `jugend_termine`
- Zeile 1132: `app.route('/jugend/<token>/termine/<int:termin_id>.ics')` → `jugend_termin_ical`
- Zeile 1158: `app.route('/erwachsen/<token>')` → `erwachsen_start`
- Zeile 1179: `app.route('/erwachsen/<token>/abzeichen')` → `erwachsen_abzeichen`
- Zeile 1197: `app.route('/erwachsen/<token>/urkunde/<int:badge_id>')` → `erwachsen_urkunde`
- Zeile 1209: `app.route('/erwachsen/<token>/ergebnisse')` → `erwachsen_ergebnisse`
- Zeile 1223: `app.route('/erwachsen/<token>/statistik')` → `erwachsen_statistik`
- Zeile 1228: `app.route('/erwachsen/<token>/termine')` → `erwachsen_termine`
- Zeile 1235: `app.route('/erwachsen/<token>/termine/<int:termin_id>.ics')` → `erwachsen_termin_ical`
- Zeile 1260: `app.route('/erwachsen/<token>/ergebnis-hochladen', methods=['GET', 'POST'])` → `erwachsen_ergebnis_upload`
- Zeile 1316: `app.route('/erwachsen/<token>/ergebnis-speichern', methods=['POST'])` → `erwachsen_ergebnis_save`
- Zeile 1335: `app.route('/erwachsen/<token>/ergebnis/<int:training_id>/bearbeiten', methods=['GET', 'POST'])` → `erwachsen_ergebnis_bearbeiten`
- Zeile 1371: `app.route('/erwachsen/<token>/ergebnis/<int:training_id>/loeschen', methods=['POST'])` → `erwachsen_ergebnis_loeschen`
- Zeile 1383: `app.route('/betreuer/login', methods=['GET', 'POST'])` → `betreuer_login`
- Zeile 1397: `app.route('/betreuer/logout', methods=['POST'])` → `betreuer_logout`
- Zeile 1403: `app.route('/betreuer')` → `betreuer_dashboard`
- Zeile 1464: `app.route('/betreuer/gluecksscheibe', methods=['GET', 'POST'])` → `betreuer_gluecksscheibe`
- Zeile 1509: `app.route('/betreuer/termine', methods=['GET', 'POST'])` → `betreuer_termine`
- Zeile 1529: `app.route('/betreuer/termine/<int:id>/edit', methods=['GET', 'POST'])` → `betreuer_termin_edit`
- Zeile 1551: `app.route('/betreuer/termine/<int:id>/delete', methods=['POST'])` → `betreuer_termin_delete`
- Zeile 1560: `app.route('/betreuer/youths', methods=['GET', 'POST'])` → `betreuer_youths`
- Zeile 1581: `app.route('/betreuer/youths/<int:id>/edit', methods=['GET', 'POST'])` → `betreuer_youth_edit`
- Zeile 1607: `app.route('/betreuer/auszeichnungen/<bereich>/<int:mitglied_id>', methods=['GET', 'POST'])` → `betreuer_auszeichnungen`
- Zeile 1667: `app.route('/betreuer/youths/<int:id>/age-class-reviewed', methods=['POST'])` → `betreuer_youth_age_class_reviewed`
- Zeile 1677: `app.route('/betreuer/youths/<int:id>/delete', methods=['POST'])` → `betreuer_youth_delete`
- Zeile 1683: `app.route('/betreuer/youths/<int:id>/qr.png')` → `betreuer_youth_qr`
- Zeile 1739: `app.route('/betreuer/qr-codes.zip')` → `betreuer_qr_codes_zip`
- Zeile 1759: `app.route('/betreuer/erwachsene', methods=['GET', 'POST'])` → `betreuer_erwachsene`
- Zeile 1783: `app.route('/betreuer/erwachsene/<int:id>/edit', methods=['GET', 'POST'])` → `betreuer_erwachsener_edit`
- Zeile 1815: `app.route('/betreuer/erwachsene/<int:id>/ergebnisse')` → `betreuer_erwachsener_ergebnisse`
- Zeile 1824: `app.route('/betreuer/erwachsene/<int:id>/ergebnisse/<int:training_id>/edit', methods=['GET', 'POST'])` → `betreuer_erwachsener_ergebnis_edit`
- Zeile 1856: `app.route('/betreuer/erwachsene/<int:id>/ergebnisse/<int:training_id>/delete', methods=['POST'])` → `betreuer_erwachsener_ergebnis_delete`
- Zeile 1867: `app.route('/betreuer/erwachsene/<int:id>/delete', methods=['POST'])` → `betreuer_erwachsener_delete`
- Zeile 1875: `app.route('/betreuer/erwachsene/<int:id>/qr.png')` → `betreuer_erwachsener_qr`
- Zeile 1922: `app.route('/betreuer/training', methods=['GET', 'POST'])` → `betreuer_training`
- Zeile 1941: `app.route('/betreuer/training/kind/<int:jugendlicher_id>')` → `betreuer_training_kid`
- Zeile 1949: `app.route('/betreuer/training/neu')` → `betreuer_training_new`
- Zeile 1957: `app.route('/betreuer/training/<int:id>/edit', methods=['GET', 'POST'])` → `betreuer_training_edit`
- Zeile 1980: `app.route('/betreuer/training/<int:id>/delete', methods=['POST'])` → `betreuer_training_delete`
- Zeile 1992: `app.route('/betreuer/meyton', methods=['GET', 'POST'])` → `betreuer_meyton`
- Zeile 2020: `app.route('/betreuer/meyton/speichern', methods=['POST'])` → `betreuer_meyton_save`
- Zeile 2035: `app.route('/betreuer/badges', defaults={'bereich': 'Jugend'}, methods=['GET', 'POST'])` → `betreuer_badges`
- Zeile 2036: `app.route('/betreuer/badges/<bereich>', methods=['GET', 'POST'])` → `betreuer_badges`
- Zeile 2171: `app.route('/betreuer/badges/<int:id>/edit', methods=['GET', 'POST'])` → `betreuer_badge_edit`
- Zeile 2224: `app.route('/betreuer/badges/<int:id>/delete', methods=['POST'])` → `betreuer_badge_delete`

## Jugendlicher
- `id = db.Column(db.Integer, primary_key=True)`
- `vorname = db.Column(db.String(50), nullable=False)`
- `nachname = db.Column(db.String(50), nullable=False)`
- `geburtsdatum = db.Column(db.String(10))`
- `geschlecht = db.Column(db.String(10))`
- `abzeichen_altersklasse_bestaetigt = db.Column(db.String(20))`
- `disziplin = db.Column(db.String(50), nullable=False, default=DISZIPLINEN[2])`
- `einstellungen_notiz = db.Column(db.String(1000))`
- `schaftkappe_position = db.Column(db.String(20))`
- `schaftbacke_position = db.Column(db.String(100))`
- `diopter_einstellung = db.Column(db.String(100))`
- `waffe = db.Column(db.String(100))`
- `aktiv = db.Column(db.Boolean, default=True, nullable=False)`
- `qr_token = db.Column(db.String(64), unique=True, nullable=False, default=lambda: secrets.token_urlsafe(24))`
- `trainings = db.relationship('Training', backref='schuetze', lazy=True, cascade='all, delete-orphan')`

## Erwachsener
- `id = db.Column(db.Integer, primary_key=True)`
- `vorname = db.Column(db.String(50), nullable=False)`
- `nachname = db.Column(db.String(50), nullable=False)`
- `geburtsdatum = db.Column(db.String(10), nullable=False)`
- `geschlecht = db.Column(db.String(10), nullable=False)`
- `disziplin = db.Column(db.String(50), nullable=False, default='Luftgewehr Auflage')`
- `einstellungen_notiz = db.Column(db.String(1000))`
- `schaftkappe_position = db.Column(db.String(20))`
- `schaftbacke_position = db.Column(db.String(100))`
- `diopter_einstellung = db.Column(db.String(100))`
- `waffe = db.Column(db.String(100))`
- `aktiv = db.Column(db.Boolean, default=True, nullable=False)`
- `qr_token = db.Column(db.String(64), unique=True, nullable=False, default=lambda: secrets.token_urlsafe(24))`
- `trainings = db.relationship('ErwachsenenTraining', backref='schuetze', lazy=True, cascade='all, delete-orphan')`

## Abzeichen
- `id = db.Column(db.Integer, primary_key=True)`
- `name = db.Column(db.String(100), nullable=False)`
- `disziplin = db.Column(db.String(50), nullable=False)`
- `ringzahl_erforderlich = db.Column(db.Float, nullable=False)`
- `wiederholungen = db.Column(db.Integer, nullable=False, default=1)`
- `reihe = db.Column(db.String(80), nullable=False, default='Allgemein')`
- `beschreibung = db.Column(db.Text)`
- `stufe = db.Column(db.Integer, default=1)`
- `alter_min = db.Column(db.Integer)`
- `alter_max = db.Column(db.Integer)`
- `zielklasse = db.Column(db.String(40))`
- `schuss_anzahl = db.Column(db.Integer)`
- `bereich = db.Column(db.String(20), nullable=False, default='Jugend')`
- `zyklus = db.Column(db.String(20), nullable=False, default='dauerhaft')`
- `wertung_basis = db.Column(db.String(12), nullable=False, default='zehntel')`

## Training
- `id = db.Column(db.Integer, primary_key=True)`
- `jugendlicher_id = db.Column(db.Integer, db.ForeignKey('jugendlicher.id'), nullable=False)`
- `datum = db.Column(db.String(10), nullable=False, default=lambda: datetime.now().strftime('%Y-%m-%d'))`
- `disziplin = db.Column(db.String(50), nullable=False, default=DISZIPLINEN[2])`
- `ringzahl = db.Column(db.Float, nullable=False)`
- `schuss_anzahl = db.Column(db.Integer, default=40)`
- `serie1 = db.Column(db.Float)`
- `serie2 = db.Column(db.Float)`
- `serie3 = db.Column(db.Float)`
- `ganzringe = db.Column(db.Integer)`
- `serien = db.Column(db.Text)`
- `zaehler = db.Column(db.Text)`
- `innenzehner = db.Column(db.Integer)`
- `weiteste = db.Column(db.Text)`
- `beste_teiler = db.Column(db.Text)`
- `trefferkreis = db.Column(db.Float)`
- `trefferlage_links = db.Column(db.Float)`
- `trefferlage_tief = db.Column(db.Float)`
- `uhrzeit = db.Column(db.String(10))`
- `zielscheibe = db.Column(db.String(100))`
- `klasse = db.Column(db.String(40))`
- `wertung = db.Column(db.String(40))`
- `startnummer = db.Column(db.String(20))`
- `standnummer = db.Column(db.String(20))`
- `bemerkung = db.Column(db.String(200))`

## ErwachsenenTraining
- `id = db.Column(db.Integer, primary_key=True)`
- `erwachsener_id = db.Column(db.Integer, db.ForeignKey('erwachsener.id'), nullable=False)`
- `datum = db.Column(db.String(10), nullable=False, default=lambda: datetime.now().strftime('%Y-%m-%d'))`
- `disziplin = db.Column(db.String(50), nullable=False, default=DISZIPLINEN[2])`
- `ringzahl = db.Column(db.Float, nullable=False)`
- `schuss_anzahl = db.Column(db.Integer, default=40)`
- `serie1 = db.Column(db.Float)`
- `serie2 = db.Column(db.Float)`
- `serie3 = db.Column(db.Float)`
- `serie4 = db.Column(db.Float)`
- `ganzringe = db.Column(db.Integer)`
- `serien = db.Column(db.Text)`
- `zaehler = db.Column(db.Text)`
- `innenzehner = db.Column(db.Integer)`
- `weiteste = db.Column(db.Text)`
- `beste_teiler = db.Column(db.Text)`
- `trefferkreis = db.Column(db.Float)`
- `trefferlage_links = db.Column(db.Float)`
- `trefferlage_tief = db.Column(db.Float)`
- `uhrzeit = db.Column(db.String(10))`
- `zielscheibe = db.Column(db.String(100))`
- `klasse = db.Column(db.String(40))`
- `wertung = db.Column(db.String(40))`
- `startnummer = db.Column(db.String(20))`
- `standnummer = db.Column(db.String(20))`
- `bemerkung = db.Column(db.String(200))`

## VerliehenesAbzeichen
- `id = db.Column(db.Integer, primary_key=True)`
- `bereich = db.Column(db.String(20), nullable=False)`
- `mitglied_id = db.Column(db.Integer, nullable=False)`
- `abzeichen_id = db.Column(db.Integer, db.ForeignKey('abzeichen.id'), nullable=False)`
- `datum = db.Column(db.String(10), nullable=False, default=lambda: date.today().isoformat())`

## JugendAbzeichenHinweis
- `id = db.Column(db.Integer, primary_key=True)`
- `jugendlicher_id = db.Column(db.Integer, db.ForeignKey('jugendlicher.id'), nullable=False)`
- `abzeichen_id = db.Column(db.Integer, db.ForeignKey('abzeichen.id'), nullable=False)`
- `gesehen = db.Column(db.Boolean, nullable=False, default=False)`
- `__table_args__ = (db.UniqueConstraint('jugendlicher_id', 'abzeichen_id', name='uq_jugend_abzeichen_hinweis'),)`

## GluecksscheibeRunde
- `id = db.Column(db.Integer, primary_key=True)`
- `datum = db.Column(db.String(10), nullable=False, default=lambda: date.today().isoformat())`
- `wuerfelzahl = db.Column(db.Integer, nullable=False)`
- `teilnahmen = db.relationship('GluecksscheibeTeilnahme', backref='runde', lazy=True, cascade='all, delete-orphan')`

## GluecksscheibeTeilnahme
- `id = db.Column(db.Integer, primary_key=True)`
- `runde_id = db.Column(db.Integer, db.ForeignKey('gluecksscheibe_runde.id'), nullable=False)`
- `jugendlicher_id = db.Column(db.Integer, db.ForeignKey('jugendlicher.id'), nullable=False)`
- `ringzahl = db.Column(db.Float, nullable=False)`
- `jugendlicher = db.relationship('Jugendlicher')`

## Termin
- `id = db.Column(db.Integer, primary_key=True)`
- `titel = db.Column(db.String(120), nullable=False)`
- `datum = db.Column(db.String(10), nullable=False)`
- `uhrzeit = db.Column(db.String(5), nullable=False)`
- `ort = db.Column(db.String(120))`
- `beschreibung = db.Column(db.Text)`
- `zielgruppe = db.Column(db.String(20), nullable=False, default='Jugend')`