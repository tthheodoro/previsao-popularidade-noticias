"""Tests for app.utils.sentimento — sentiment analysis module."""

from app.utils.sentimento import analisar_sentimento


class TestAnalisarSentimento:
    def test_positive_phrase(self):
        result = analisar_sentimento("vitória excelente")
        assert result > 0

    def test_negative_phrase(self):
        result = analisar_sentimento("crise trágica queda")
        assert result < 0

    def test_neutral_phrase(self):
        result = analisar_sentimento("casa grande azul")
        assert result == 0

    def test_empty_string(self):
        result = analisar_sentimento("")
        assert result == 0

    def test_none_input(self):
        result = analisar_sentimento(None)
        assert result == 0

    def test_compound_exception_desemprego_cai(self):
        """'desemprego cai' is a positive exception (+2), even though 'desemprego' is negative."""
        result = analisar_sentimento("desemprego cai")
        assert result == 2

    def test_compound_exception_crise_cresce(self):
        """'crise cresce' is a negative exception (-2), even though 'cresce' is positive."""
        result = analisar_sentimento("crise cresce")
        assert result == -2

    def test_score_clamped_to_positive_max(self):
        """Many positive words should clamp at +5."""
        result = analisar_sentimento(
            "vitória excelente positivo feliz bom ganha recorde sucesso lucro avanço melhora aprovação"
        )
        assert result == 5

    def test_score_clamped_to_negative_max(self):
        """Many negative words should clamp at -5."""
        result = analisar_sentimento(
            "crise mau queda derrota trágico pior problema falha rombo desemprego tensão prejuízo crime morte risco baixa greve inflação polémica violência"
        )
        assert result == -5

    def test_score_exactly_at_clamp_boundary(self):
        """Score at exactly +5 should remain +5."""
        result = analisar_sentimento(
            "vitória excelente positivo feliz bom ganha recorde"
        )
        assert result == 5

    def test_compound_overrides_individual_words(self):
        """Compound exception is removed before counting individual words."""
        # 'desemprego cai' -> +2, and 'desemprego' is removed, so no -1 from it
        result = analisar_sentimento("desemprego cai")
        assert result == 2

    def test_mixed_positive_negative(self):
        """Mix of positive and negative words should produce intermediate score."""
        result = analisar_sentimento("vitória crise")
        assert result == 0  # +1 for vitória, -1 for crise
