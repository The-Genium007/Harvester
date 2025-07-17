"""
Analyseur de pertinence pour évaluer la qualité technique du contenu
"""
import re
import asyncio
from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class RelevanceMetrics:
    """Métriques de pertinence d'un contenu"""
    tech_keywords_score: float = 0.0
    content_depth_score: float = 0.0
    language_quality_score: float = 0.0
    structure_score: float = 0.0
    overall_score: float = 0.0


class RelevanceAnalyzer:
    """
    Analyseur de pertinence qui évalue la qualité technique
    et la pertinence d'un contenu textuel
    """
    
    def __init__(self):
        self.tech_keywords = self._load_tech_keywords()
        self.quality_indicators = self._load_quality_indicators()
        
    def _load_tech_keywords(self) -> Dict[str, float]:
        """Charge les mots-clés techniques avec leurs poids"""
        return {
            # Langages de programmation (poids élevé)
            'python': 1.0, 'javascript': 1.0, 'typescript': 1.0, 'java': 1.0,
            'golang': 1.0, 'rust': 1.0, 'php': 1.0, 'ruby': 1.0, 'c++': 1.0,
            'c#': 1.0, 'kotlin': 1.0, 'swift': 1.0, 'scala': 1.0,
            
            # Frameworks et bibliothèques
            'react': 0.9, 'vue': 0.9, 'angular': 0.9, 'svelte': 0.9,
            'django': 0.9, 'flask': 0.9, 'fastapi': 0.9, 'express': 0.9,
            'spring': 0.9, 'laravel': 0.9, 'rails': 0.9,
            
            # Technologies cloud et infrastructure
            'docker': 0.8, 'kubernetes': 0.8, 'aws': 0.8, 'azure': 0.8,
            'gcp': 0.8, 'terraform': 0.8, 'ansible': 0.8, 'jenkins': 0.8,
            
            # Bases de données
            'postgresql': 0.8, 'mysql': 0.8, 'mongodb': 0.8, 'redis': 0.8,
            'elasticsearch': 0.8, 'cassandra': 0.8,
            
            # Concepts et pratiques
            'api': 0.7, 'rest': 0.7, 'graphql': 0.7, 'microservices': 0.8,
            'devops': 0.8, 'ci/cd': 0.8, 'testing': 0.7, 'debugging': 0.7,
            'performance': 0.7, 'security': 0.8, 'authentication': 0.7,
            
            # IA et Machine Learning
            'machine learning': 1.0, 'artificial intelligence': 1.0,
            'deep learning': 1.0, 'neural networks': 1.0, 'tensorflow': 0.9,
            'pytorch': 0.9, 'scikit-learn': 0.9, 'nlp': 0.9,
            
            # Outils de développement
            'git': 0.6, 'github': 0.6, 'gitlab': 0.6, 'vscode': 0.6,
            'webpack': 0.7, 'babel': 0.7, 'npm': 0.6, 'yarn': 0.6,
            
            # Types de contenu technique
            'tutorial': 0.5, 'guide': 0.5, 'documentation': 0.6,
            'best practices': 0.7, 'architecture': 0.8, 'design patterns': 0.8,
            'algorithm': 0.8, 'data structure': 0.8
        }
        
    def _load_quality_indicators(self) -> Dict[str, float]:
        """Charge les indicateurs de qualité de contenu"""
        return {
            # Indicateurs positifs
            'code example': 0.3, 'source code': 0.3, 'github': 0.2,
            'step by step': 0.2, 'complete guide': 0.3, 'detailed': 0.2,
            'comprehensive': 0.2, 'in-depth': 0.3, 'advanced': 0.2,
            'production': 0.3, 'real world': 0.3, 'case study': 0.3,
            
            # Indicateurs de contenu éducatif
            'learn': 0.1, 'understand': 0.1, 'explain': 0.1,
            'introduction': 0.1, 'beginner': 0.1, 'getting started': 0.1,
            
            # Indicateurs de fraîcheur
            '2024': 0.2, '2023': 0.1, 'latest': 0.1, 'new': 0.1,
            'updated': 0.1, 'modern': 0.1
        }
        
    async def analyze_text(self, text: str) -> float:
        """
        Analyse la pertinence d'un texte
        
        Args:
            text: Texte à analyser (titre + description généralement)
            
        Returns:
            Score de pertinence entre 0 et 1
        """
        if not text or len(text.strip()) < 10:
            return 0.0
            
        text_lower = text.lower()
        
        # Calcul des différentes métriques
        metrics = RelevanceMetrics()
        
        # 1. Score basé sur les mots-clés techniques
        metrics.tech_keywords_score = self._calculate_tech_keywords_score(text_lower)
        
        # 2. Score de profondeur du contenu
        metrics.content_depth_score = self._calculate_content_depth_score(text_lower)
        
        # 3. Score de qualité du langage
        metrics.language_quality_score = self._calculate_language_quality_score(text)
        
        # 4. Score de structure
        metrics.structure_score = self._calculate_structure_score(text)
        
        # Calcul du score global pondéré
        metrics.overall_score = (
            metrics.tech_keywords_score * 0.4 +
            metrics.content_depth_score * 0.3 +
            metrics.language_quality_score * 0.2 +
            metrics.structure_score * 0.1
        )
        
        return min(metrics.overall_score, 1.0)
        
    def _calculate_tech_keywords_score(self, text: str) -> float:
        """Calcule le score basé sur les mots-clés techniques"""
        score = 0.0
        text_words = set(text.split())
        
        # Recherche de mots-clés exacts
        for keyword, weight in self.tech_keywords.items():
            if keyword.lower() in text:
                score += weight
                
        # Recherche de mots-clés dans les mots individuels
        for word in text_words:
            if word in self.tech_keywords:
                score += self.tech_keywords[word] * 0.5  # Poids réduit
                
        # Normalisation (divise par le nombre max possible de mots-clés)
        max_possible_score = sum(list(self.tech_keywords.values())[:10])  # Top 10
        normalized_score = min(score / max_possible_score, 1.0)
        
        return normalized_score
        
    def _calculate_content_depth_score(self, text: str) -> float:
        """Évalue la profondeur du contenu basée sur les indicateurs de qualité"""
        score = 0.0
        
        for indicator, weight in self.quality_indicators.items():
            if indicator in text:
                score += weight
                
        # Bonus pour la longueur du texte (indicateur de contenu substantiel)
        length_bonus = min(len(text) / 500, 0.3)  # Max 0.3 pour 500+ caractères
        score += length_bonus
        
        return min(score, 1.0)
        
    def _calculate_language_quality_score(self, text: str) -> float:
        """Évalue la qualité du langage utilisé"""
        score = 0.8  # Score de base
        
        # Pénalités pour des indicateurs de faible qualité
        quality_issues = [
            'click here', 'read more', 'amazing', 'incredible',
            'you won\'t believe', 'secret', 'hack'
        ]
        
        text_lower = text.lower()
        for issue in quality_issues:
            if issue in text_lower:
                score -= 0.1
                
        # Bonus pour un langage technique approprié
        technical_language = [
            'implementation', 'architecture', 'methodology',
            'framework', 'library', 'algorithm', 'optimization'
        ]
        
        for term in technical_language:
            if term in text_lower:
                score += 0.05
                
        return max(min(score, 1.0), 0.0)
        
    def _calculate_structure_score(self, text: str) -> float:
        """Évalue la structure du texte"""
        score = 0.5  # Score de base
        
        # Bonus pour une bonne structure
        if len(text) > 50:  # Titre/description suffisamment long
            score += 0.2
            
        # Vérifie la présence de mots de liaison techniques
        structure_indicators = [
            'how to', 'step by step', 'introduction to',
            'overview of', 'guide to', 'tutorial on'
        ]
        
        text_lower = text.lower()
        for indicator in structure_indicators:
            if indicator in text_lower:
                score += 0.1
                break  # Un seul bonus
                
        return min(score, 1.0)
        
    async def analyze_content_batch(self, texts: List[str]) -> List[float]:
        """
        Analyse un batch de textes en parallèle
        
        Args:
            texts: Liste de textes à analyser
            
        Returns:
            Liste des scores de pertinence
        """
        tasks = [self.analyze_text(text) for text in texts]
        scores = await asyncio.gather(*tasks)
        return scores
        
    def get_keyword_matches(self, text: str) -> List[str]:
        """
        Retourne la liste des mots-clés techniques trouvés dans le texte
        
        Args:
            text: Texte à analyser
            
        Returns:
            Liste des mots-clés trouvés
        """
        text_lower = text.lower()
        matches = []
        
        for keyword in self.tech_keywords:
            if keyword in text_lower:
                matches.append(keyword)
                
        return matches
        
    def explain_score(self, text: str) -> Dict[str, any]:
        """
        Fournit une explication détaillée du score
        
        Args:
            text: Texte analysé
            
        Returns:
            Dictionnaire avec les détails du scoring
        """
        text_lower = text.lower()
        
        explanation = {
            'overall_score': 0.0,
            'tech_keywords_found': self.get_keyword_matches(text),
            'quality_indicators_found': [],
            'text_length': len(text),
            'breakdown': {}
        }
        
        # Collecte les indicateurs de qualité trouvés
        for indicator in self.quality_indicators:
            if indicator in text_lower:
                explanation['quality_indicators_found'].append(indicator)
                
        # Calcul détaillé
        metrics = RelevanceMetrics()
        metrics.tech_keywords_score = self._calculate_tech_keywords_score(text_lower)
        metrics.content_depth_score = self._calculate_content_depth_score(text_lower)
        metrics.language_quality_score = self._calculate_language_quality_score(text)
        metrics.structure_score = self._calculate_structure_score(text)
        
        metrics.overall_score = (
            metrics.tech_keywords_score * 0.4 +
            metrics.content_depth_score * 0.3 +
            metrics.language_quality_score * 0.2 +
            metrics.structure_score * 0.1
        )
        
        explanation['overall_score'] = min(metrics.overall_score, 1.0)
        explanation['breakdown'] = {
            'tech_keywords_score': metrics.tech_keywords_score,
            'content_depth_score': metrics.content_depth_score,
            'language_quality_score': metrics.language_quality_score,
            'structure_score': metrics.structure_score
        }
        
        return explanation
