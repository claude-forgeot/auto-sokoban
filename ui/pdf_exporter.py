"""Export des résultats de résolution en PDF : tableau comparatif + explications."""

from __future__ import annotations

from pathlib import Path
from datetime import datetime

# Pour PDF : reportlab (import différé pour ne pas crasher le jeu si absent)
_REPORTLAB_AVAILABLE = False
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch, cm
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    )
    from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
    from reportlab.lib import colors
    _REPORTLAB_AVAILABLE = True
except ImportError:
    pass

from game.board import BoardState
from solver.base import SolverResult


class PDFExporter:
    """Exporte un rapport PDF : tableau comparatif des 3 algorithmes + explications."""

    def __init__(self, output_path: str | Path):
        self.output_path = Path(output_path)
        self.output_path.parent.mkdir(parents=True, exist_ok=True)

    def export(
        self,
        level_name: str,
        initial_state: BoardState,
        results: list[SolverResult],
    ) -> Path:
        """Crée un rapport PDF comparatif.

        Args:
            level_name: Nom du niveau (ex: "facile/microban_009")
            initial_state: État initial du plateau
            results: Résultats des solveurs (A*, BFS, DFS)
        Returns:
            Chemin du fichier PDF généré
        """
        if not _REPORTLAB_AVAILABLE:
            raise ImportError(
                "reportlab est requis pour exporter en PDF. "
                "Installez-le avec : pip install reportlab"
            )

        doc = SimpleDocTemplate(
            str(self.output_path),
            pagesize=A4,
            rightMargin=1.5 * cm,
            leftMargin=1.5 * cm,
            topMargin=1.5 * cm,
            bottomMargin=1.5 * cm,
        )

        styles = getSampleStyleSheet()
        story: list = []

        # ===== TITRE =====
        story.append(self._build_title(level_name, styles))
        story.append(Spacer(1, 0.3 * inch))

        # ===== INFOS NIVEAU =====
        story.append(self._build_level_info(level_name, initial_state, styles))
        story.append(Spacer(1, 0.3 * inch))

        # ===== TABLEAU COMPARATIF =====
        story.append(self._build_results_table(results, styles))
        story.append(Spacer(1, 0.4 * inch))

        # ===== EXPLICATIONS DÉTAILLÉES =====
        story.extend(self._build_detailed_explanation(results, styles))

        # Générer le PDF
        doc.build(story)
        return self.output_path

    # ------------------------------------------------------------------
    # Composants du PDF
    # ------------------------------------------------------------------

    def _build_title(self, level_name: str, styles) -> Paragraph:
        """Titre du rapport."""
        style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=22,
            textColor=colors.HexColor('#2F3B1D'),
            spaceAfter=12,
            alignment=TA_CENTER,
        )
        return Paragraph(
            f"Rapport de R&eacute;solution Sokoban : {level_name}", style,
        )

    def _build_level_info(
        self, level_name: str, state: BoardState, styles,
    ) -> Paragraph:
        """Infos sur le niveau."""
        info_style = ParagraphStyle(
            'Info',
            parent=styles['Normal'],
            fontSize=11,
            textColor=colors.HexColor('#6B8E23'),
            spaceAfter=6,
        )
        timestamp = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        info_text = (
            f"<b>Niveau :</b> {level_name}<br/>"
            f"<b>Dimensions :</b> {state.width} x {state.height} cases<br/>"
            f"<b>Caisses :</b> {len(state.boxes)}<br/>"
            f"<b>Cibles :</b> {len(state.targets)}<br/>"
            f"<b>Date :</b> {timestamp}"
        )
        return Paragraph(info_text, info_style)

    def _build_results_table(
        self, results: list[SolverResult], styles,
    ) -> Table:
        """Tableau comparatif des résultats."""
        # Titre section
        heading = ParagraphStyle(
            'TableHeading',
            parent=styles['Heading2'],
            fontSize=15,
            textColor=colors.HexColor('#2F3B1D'),
            spaceAfter=10,
        )

        data = [
            ['Algorithme', 'Resultat', 'Coups', 'Noeuds Explores', 'Temps (ms)'],
        ]

        for result in results:
            status = "TROUVE" if result.found else "ECHOUE"
            moves = str(result.solution_length) if result.found else "-"
            nodes = f"{result.total_nodes_explored:,}"
            time_ms = f"{result.time_ms:.1f}"

            data.append([
                result.algo_name,
                status,
                moves,
                nodes,
                time_ms,
            ])

        col_widths = [3 * cm, 2.5 * cm, 2 * cm, 3.5 * cm, 2.5 * cm]
        table = Table(data, colWidths=col_widths)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#6B8E23')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('TOPPADDING', (0, 0), (-1, 0), 8),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#FBF5E6')),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#8B7355')),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('TOPPADDING', (0, 1), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
        ]))
        return table

    def _build_detailed_explanation(
        self,
        results: list[SolverResult],
        styles,
    ) -> list:
        """Explications détaillées pour débutants. Retourne une liste de flowables."""
        story: list = []

        heading_style = ParagraphStyle(
            'SectionHeading',
            parent=styles['Heading2'],
            fontSize=15,
            textColor=colors.HexColor('#2F3B1D'),
            spaceAfter=10,
            spaceBefore=6,
        )

        body_style = ParagraphStyle(
            'Body',
            parent=styles['Normal'],
            fontSize=10,
            alignment=TA_JUSTIFY,
            spaceAfter=8,
            leading=14,
        )

        # ----- 1. Qu'est-ce que chaque algo fait ? -----
        story.append(Paragraph(
            "<b>1. Qu'est-ce que chaque algorithme fait ?</b>", heading_style,
        ))

        explanations = [
            (
                "A* (A-Star)",
                "A* est le plus intelligent des trois. Il utilise une <i>heuristique</i> "
                "(une estimation) de la distance vers la solution. C'est comme si vous "
                "demandiez a quelqu'un qui connait le trajet de vous guider. A* explore "
                "d'abord les chemins les plus prometteurs, ce qui le rend generalement "
                "plus rapide.",
            ),
            (
                "BFS (Breadth-First Search)",
                "BFS explore tous les chemins niveau par niveau, comme une onde qui "
                "s'etend. C'est methodique et garantit la solution la plus courte "
                "(en nombre de coups), mais c'est lent sur les gros problemes car il "
                "explore <i>beaucoup</i> d'etats inutiles.",
            ),
            (
                "DFS (Depth-First Search)",
                "DFS explore un chemin jusqu'au bout avant de revenir en arriere. "
                "C'est comme essayer de sortir d'un labyrinthe en collant la main "
                "gauche au mur. DFS peut trouver une solution rapidement, mais elle "
                "n'est pas forcement optimale.",
            ),
        ]

        for name, expl in explanations:
            story.append(Paragraph(f"<b>{name} :</b> {expl}", body_style))

        story.append(Spacer(1, 0.1 * inch))

        # ----- 2. Qu'est-ce qui s'est passé ? -----
        story.append(Paragraph(
            "<b>2. Qu'est-ce qui s'est passe ?</b>", heading_style,
        ))

        found_count = sum(1 for r in results if r.found)
        if found_count == len(results):
            interpretation = (
                "<b>Tous les algorithmes ont trouve une solution !</b><br/><br/>"
                "Les trois methodes ont reussi a resoudre le puzzle. Cela signifie que "
                "le niveau n'est pas en <i>deadlock</i> (caisses irremediablement "
                "bloquees). Vous pouvez voir les differences de performance dans le "
                "tableau ci-dessus :<br/>"
                "- <b>A*</b> explore generalement moins de noeuds (plus intelligent)<br/>"
                "- <b>BFS</b> trouve la vraie solution optimale<br/>"
                "- <b>DFS</b> peut explorer plus mais etre plus rapide"
            )
        elif found_count == 0:
            interpretation = (
                "<b>Aucun algorithme n'a trouve de solution.</b><br/><br/>"
                "Cela peut signifier :<br/>"
                "1. Le niveau est en deadlock : les caisses sont bloquees.<br/>"
                "2. Le probleme est trop complexe pour le timeout defini.<br/>"
                "3. DFS a atteint sa profondeur maximale."
            )
        else:
            failed = [r.algo_name for r in results if not r.found]
            interpretation = (
                f"<b>{len(failed)} algorithme(s) n'ont pas trouve de solution : "
                f"{', '.join(failed)}.</b><br/><br/>"
                "Cela peut signifier :<br/>"
                "1. <b>Le niveau est complexe :</b> la solution demande beaucoup de "
                "coups et l'espace de recherche est enorme.<br/>"
                "2. <b>Timeout atteint :</b> le delai n'etait pas suffisant.<br/>"
                "3. <b>Profondeur DFS :</b> DFS est limite a 200 coups de profondeur."
            )

        story.append(Paragraph(interpretation, body_style))
        story.append(Spacer(1, 0.1 * inch))

        # ----- 3. Qu'est-ce qu'un noeud ? -----
        story.append(Paragraph(
            "<b>3. Qu'est-ce qu'un 'noeud' ?</b>", heading_style,
        ))

        story.append(Paragraph(
            "Un <b>noeud</b> represente un <i>etat unique du plateau</i>. Chaque "
            "position du joueur et des caisses = un noeud different. Les algorithmes "
            "explorent de nombreux noeuds pour trouver le chemin (la sequence d'etats) "
            "menant a la solution.<br/><br/>"
            "<b>Plus de noeuds explores</b> = l'algo a du chercher plus longtemps "
            "(soit c'est un probleme dur, soit l'algo est moins intelligent).",
            body_style,
        ))
        story.append(Spacer(1, 0.1 * inch))

        # ----- 4. Comparaison de performance -----
        story.append(Paragraph(
            "<b>4. Comparaison de Performance</b>", heading_style,
        ))

        fastest = min(results, key=lambda r: r.time_ms)
        least_nodes = min(results, key=lambda r: r.total_nodes_explored)

        story.append(Paragraph(
            f"<b>Le plus rapide :</b> {fastest.algo_name} "
            f"({fastest.time_ms:.1f} ms)<br/>"
            f"<b>Moins de noeuds explores :</b> {least_nodes.algo_name} "
            f"({least_nodes.total_nodes_explored:,} noeuds)<br/><br/>"
            "A* est generalement plus efficace car il 'sait' ou aller grace a "
            "son heuristique. BFS est garanti optimal mais explore plus. "
            "DFS depend de la structure du probleme.",
            body_style,
        ))
        story.append(Spacer(1, 0.1 * inch))

        # ----- 5. Conseil pratique -----
        story.append(Paragraph(
            "<b>5. Conseil pour Resoudre Manuellement</b>", heading_style,
        ))

        story.append(Paragraph(
            "Si vous voulez resoudre ce puzzle vous-meme :<br/>"
            "1. <b>Analysez les cibles :</b> Ou doivent aller les caisses ?<br/>"
            "2. <b>Cherchez les deadlocks :</b> Quelles caisses ne peuvent pas "
            "revenir en arriere ?<br/>"
            "3. <b>Planifiez l'ordre :</b> Quelle caisse placer en premier ?<br/>"
            "4. <b>Testez avec UNDO :</b> Vous pouvez annuler chaque mouvement "
            "en jeu.<br/><br/>"
            "La plupart des puzzles Sokoban se resolvent par essais-erreurs et "
            "logique, mais les plus difficiles demandent de la planification "
            "strategique.",
            body_style,
        ))

        return story