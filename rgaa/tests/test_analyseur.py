import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "files"))

from analyseur import analyser_html

HTML_ALT_MANQUANT = """
<html lang="fr"><head><title>Test</title><meta charset="utf-8"></head>
<body>
  <img src="logo.png" id="logo">
  <img src="deco.png" alt="">
  <img src="chat.png" alt="Un chat">
</body></html>
"""

HTML_CONFORME = """
<html lang="fr"><head><title>Test</title><meta charset="utf-8"></head>
<body><h1>Titre</h1><p>Contenu</p></body></html>
"""

HTML_IFRAME_SANS_TITLE = """
<html lang="fr"><head><title>T</title><meta charset="utf-8"></head>
<body><iframe src="video.html"></iframe></body></html>
"""

HTML_LIEN_VIDE = """
<html lang="fr"><head><title>T</title><meta charset="utf-8"></head>
<body><a href="/page">Lien valide</a><a href="/autre"></a></body></html>
"""

HTML_SANS_LANG = """
<html><head><title>T</title><meta charset="utf-8"></head>
<body><p>Contenu</p></body></html>
"""


class TestTheme1:
    def test_detecte_alt_manquant(self):
        result = analyser_html(HTML_ALT_MANQUANT)
        critere = next((c for c in result["criteres"] if c["id"] == "1.1"), None)
        assert critere is not None
        assert critere["statut"] == "NC"
        assert any("logo" in e["selecteur"] for e in critere["elements"])

    def test_ignore_image_decorative_avec_alt_vide(self):
        result = analyser_html(HTML_ALT_MANQUANT)
        critere = next((c for c in result["criteres"] if c["id"] == "1.1"), None)
        assert not any("deco" in e["selecteur"] for e in critere["elements"])


class TestTheme2:
    def test_detecte_iframe_sans_title(self):
        result = analyser_html(HTML_IFRAME_SANS_TITLE)
        critere = next((c for c in result["criteres"] if c["id"] == "2.1"), None)
        assert critere is not None
        assert critere["statut"] == "NC"

    def test_pas_de_violation_si_pas_d_iframe(self):
        result = analyser_html(HTML_CONFORME)
        critere = next((c for c in result["criteres"] if c["id"] == "2.1"), None)
        if critere:
            assert critere["statut"] == "C"


class TestTheme6:
    def test_detecte_lien_sans_intitule(self):
        result = analyser_html(HTML_LIEN_VIDE)
        critere = next((c for c in result["criteres"] if c["id"] == "6.1"), None)
        assert critere is not None
        assert critere["statut"] == "NC"


class TestTheme8:
    def test_detecte_html_sans_lang(self):
        result = analyser_html(HTML_SANS_LANG)
        critere = next((c for c in result["criteres"] if c["id"] == "8.3"), None)
        assert critere is not None
        assert critere["statut"] == "NC"

    def test_html_conforme_lang(self):
        result = analyser_html(HTML_CONFORME)
        critere = next((c for c in result["criteres"] if c["id"] == "8.3"), None)
        if critere:
            assert critere["statut"] == "C"


class TestStructure:
    def test_champs_requis(self):
        result = analyser_html(HTML_CONFORME)
        assert "themes_analyses" in result
        assert "nb_violations" in result
        assert "criteres" in result
        assert "note" in result

    def test_chaque_critere_a_statut(self):
        result = analyser_html(HTML_ALT_MANQUANT)
        for c in result["criteres"]:
            assert c["statut"] in ("C", "NC")
            assert "elements" in c


# ============================================================================
# Test Gap Coverage (12 unit tests for 82% → 95% coverage)
# ============================================================================

class TestDecorativeImagesAriaHidden:
    """Tests for aria-hidden="true" image detection (line 66)"""

    def test_aria_hidden_true_marked_as_decorative(self):
        """Image with aria-hidden="true" should be excluded from violations"""
        html = """
        <html lang="fr"><head><title>Test</title><meta charset="utf-8"></head>
        <body>
          <img src="deco.png" aria-hidden="true">
        </body></html>
        """
        result = analyser_html(html)
        critere = next((c for c in result["criteres"] if c["id"] == "1.1"), None)
        assert critere is not None
        assert critere["statut"] == "C"
        assert len(critere["elements"]) == 0

    def test_aria_hidden_false_not_decorative(self):
        """Image with aria-hidden="false" should be checked for alt"""
        html = """
        <html lang="fr"><head><title>Test</title><meta charset="utf-8"></head>
        <body>
          <img src="important.png" aria-hidden="false">
        </body></html>
        """
        result = analyser_html(html)
        critere = next((c for c in result["criteres"] if c["id"] == "1.1"), None)
        assert critere is not None
        assert critere["statut"] == "NC"
        assert len(critere["elements"]) > 0


class TestTableDescriptionVariants:
    """Tests for table caption/summary detection (lines 101-113)"""

    def test_table_with_caption_and_summary(self):
        """Table with both caption and summary should be compliant"""
        html = """
        <html lang="fr"><head><title>Test</title><meta charset="utf-8"></head>
        <body>
          <table summary="Résumé du tableau">
            <caption>Titre du tableau</caption>
            <tr><th scope="col">Col1</th></tr>
          </table>
        </body></html>
        """
        result = analyser_html(html)
        critere = next((c for c in result["criteres"] if c["id"] == "5.1"), None)
        assert critere is not None
        assert critere["statut"] == "C"

    def test_table_with_caption_only(self):
        """Table with caption but no summary should be compliant"""
        html = """
        <html lang="fr"><head><title>Test</title><meta charset="utf-8"></head>
        <body>
          <table>
            <caption>Titre du tableau</caption>
            <tr><th scope="col">Col1</th></tr>
          </table>
        </body></html>
        """
        result = analyser_html(html)
        critere = next((c for c in result["criteres"] if c["id"] == "5.1"), None)
        assert critere is not None
        assert critere["statut"] == "C"

    def test_table_with_summary_only(self):
        """Table with summary but no caption should be compliant"""
        html = """
        <html lang="fr"><head><title>Test</title><meta charset="utf-8"></head>
        <body>
          <table summary="Résumé du tableau">
            <tr><th scope="col">Col1</th></tr>
          </table>
        </body></html>
        """
        result = analyser_html(html)
        critere = next((c for c in result["criteres"] if c["id"] == "5.1"), None)
        assert critere is not None
        assert critere["statut"] == "C"

    def test_table_with_neither_caption_nor_summary(self):
        """Table without caption, summary, aria-label, or aria-describedby should fail"""
        html = """
        <html lang="fr"><head><title>Test</title><meta charset="utf-8"></head>
        <body>
          <table>
            <tr><th scope="col">Col1</th></tr>
          </table>
        </body></html>
        """
        result = analyser_html(html)
        critere = next((c for c in result["criteres"] if c["id"] == "5.1"), None)
        assert critere is not None
        assert critere["statut"] == "NC"
        assert len(critere["elements"]) > 0

    def test_table_with_aria_label(self):
        """Table with aria-label should be compliant"""
        html = """
        <html lang="fr"><head><title>Test</title><meta charset="utf-8"></head>
        <body>
          <table aria-label="Données principales">
            <tr><th scope="col">Col1</th></tr>
          </table>
        </body></html>
        """
        result = analyser_html(html)
        critere = next((c for c in result["criteres"] if c["id"] == "5.1"), None)
        assert critere is not None
        assert critere["statut"] == "C"


class TestHeadingHierarchyJumps:
    """Tests for heading level jumps detection (lines 196-197)"""

    def test_heading_jump_h1_to_h4_violation(self):
        """Jump from h1 to h4 (skip > 1) should be flagged as violation"""
        html = """
        <html lang="fr"><head><title>Test</title><meta charset="utf-8"></head>
        <body>
          <h1>Titre 1</h1>
          <h4>Titre 4</h4>
        </body></html>
        """
        result = analyser_html(html)
        critere = next((c for c in result["criteres"] if c["id"] == "9.2"), None)
        assert critere is not None
        assert critere["statut"] == "NC"
        assert len(critere["elements"]) > 0
        assert "h1 → h4" in critere["elements"][0]["probleme"]

    def test_heading_valid_progression_h1_to_h2(self):
        """Valid progression from h1 to h2 (skip = 1) should be allowed"""
        html = """
        <html lang="fr"><head><title>Test</title><meta charset="utf-8"></head>
        <body>
          <h1>Titre 1</h1>
          <h2>Titre 2</h2>
        </body></html>
        """
        result = analyser_html(html)
        critere = next((c for c in result["criteres"] if c["id"] == "9.2"), None)
        assert critere is not None
        assert critere["statut"] == "C"
        assert len(critere["elements"]) == 0


class TestFormFieldExclusion:
    """Tests for form field type exclusion (lines 215-224)"""

    def test_input_button_type_excluded(self):
        """Input type="button" should be excluded from label requirement"""
        html = """
        <html lang="fr"><head><title>Test</title><meta charset="utf-8"></head>
        <body>
          <input type="button" value="Click me">
        </body></html>
        """
        result = analyser_html(html)
        critere = next((c for c in result["criteres"] if c["id"] == "11.1"), None)
        assert critere is not None
        assert critere["statut"] == "C"
        assert len(critere["elements"]) == 0

    def test_input_text_type_requires_label(self):
        """Input type="text" should require label or aria-label"""
        html = """
        <html lang="fr"><head><title>Test</title><meta charset="utf-8"></head>
        <body>
          <input type="text">
        </body></html>
        """
        result = analyser_html(html)
        critere = next((c for c in result["criteres"] if c["id"] == "11.1"), None)
        assert critere is not None
        assert critere["statut"] == "NC"
        assert len(critere["elements"]) > 0


class TestCssClassSelectorHandling:
    """Tests for CSS class selector in selecteur (line 268)"""

    def test_input_with_multiple_classes(self):
        """Input with multiple classes should use first 2 in selector"""
        html = """
        <html lang="fr"><head><title>Test</title><meta charset="utf-8"></head>
        <body>
          <input type="text" class="field-primary field-large field-required">
        </body></html>
        """
        result = analyser_html(html)
        critere = next((c for c in result["criteres"] if c["id"] == "11.1"), None)
        assert critere is not None
        assert critere["statut"] == "NC"
        # Verify that the selecteur includes classes
        assert any("field-primary" in e["selecteur"] for e in critere["elements"])


class TestComplexScenario:
    """Test combining multiple violations in one page"""

    def test_complex_page_multiple_violations(self):
        """Complex page with multiple violations should report all"""
        html = """
        <html lang="fr"><head><title>Test</title><meta charset="utf-8"></head>
        <body>
          <img src="deco.png" aria-hidden="true">
          <img src="important.png">
          <table>
            <tr><th>Header</th></tr>
          </table>
          <h1>Title</h1>
          <h4>Subsection</h4>
          <input type="text">
          <a href="/page"></a>
        </body></html>
        """
        result = analyser_html(html)
        assert result["nb_violations"] > 0
        # Should detect: missing alt on img, table without description, heading jump, unlabeled input, empty link
        theme1 = next((c for c in result["criteres"] if c["id"] == "1.1"), None)
        theme5 = next((c for c in result["criteres"] if c["id"] == "5.1"), None)
        theme6 = next((c for c in result["criteres"] if c["id"] == "6.1"), None)
        theme9 = next((c for c in result["criteres"] if c["id"] == "9.2"), None)
        theme11 = next((c for c in result["criteres"] if c["id"] == "11.1"), None)

        assert theme1 and theme1["statut"] == "NC"  # missing alt
        assert theme5 and theme5["statut"] == "NC"  # table without description
        assert theme6 and theme6["statut"] == "NC"  # empty link
        assert theme9 and theme9["statut"] == "NC"  # heading jump
        assert theme11 and theme11["statut"] == "NC"  # unlabeled input


def _critere(res, cid):
    return next(c for c in res["criteres"] if c["id"] == cid)


class TestCouvertureManquante:
    """Chemins NC non couverts auparavant (review #25/#26/#50)."""

    def test_theme12_skip_link_absent_est_NC(self):
        html = '<html lang="fr"><head><title>T</title><meta charset="utf-8"></head><body><p>x</p></body></html>'
        res = analyser_html(html, [12])
        assert _critere(res, "12.11")["statut"] == "NC"

    def test_theme12_skip_link_present_est_C(self):
        html = '<html lang="fr"><head><title>T</title><meta charset="utf-8"></head><body><a href="#contenu">Aller au contenu</a></body></html>'
        res = analyser_html(html, [12])
        assert _critere(res, "12.11")["statut"] == "C"

    def test_theme5_7_th_sans_scope_est_NC(self):
        html = '<html lang="fr"><head><title>T</title><meta charset="utf-8"></head><body><table><caption>c</caption><tr><th>H</th></tr></table></body></html>'
        res = analyser_html(html, [5])
        assert _critere(res, "5.7")["statut"] == "NC"

    def test_theme8_5_title_vide_est_NC(self):
        html = '<html lang="fr"><head><title></title><meta charset="utf-8"></head><body></body></html>'
        res = analyser_html(html, [8])
        assert _critere(res, "8.5")["statut"] == "NC"

    def test_theme8_6_charset_absent_est_NC(self):
        html = '<html lang="fr"><head><title>T</title></head><body></body></html>'
        res = analyser_html(html, [8])
        assert _critere(res, "8.6")["statut"] == "NC"
