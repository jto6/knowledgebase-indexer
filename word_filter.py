#!/usr/bin/env python3
"""
Significant word filtering for technical document indexing.

Filters out common words that are not useful for technical book indexes,
keeping only words that refer to specific objects, concepts, or technical terms.
"""

import re
from typing import Set, List, Dict, Tuple
from collections import Counter


class SignificantWordFilter:
    """Filters text to extract only significant words suitable for technical indexing."""
    
    def __init__(self):
        """Initialize the filter with comprehensive stop word lists."""
        
        # Common English stop words
        self.stop_words = {
            # Articles
            'a', 'an', 'the',
            
            # Pronouns
            'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her', 'us', 'them',
            'my', 'your', 'his', 'her', 'its', 'our', 'their', 'mine', 'yours', 'hers', 'ours', 'theirs',
            'myself', 'yourself', 'himself', 'herself', 'itself', 'ourselves', 'yourselves', 'themselves',
            'this', 'that', 'these', 'those', 'who', 'whom', 'whose', 'which', 'what',
            
            # Conjunctions
            'and', 'or', 'but', 'nor', 'for', 'so', 'yet', 'because', 'since', 'unless', 'until',
            'while', 'whereas', 'although', 'though', 'if', 'whether', 'either', 'neither',
            
            # Prepositions
            'in', 'on', 'at', 'by', 'with', 'without', 'through', 'over', 'under', 'above', 'below',
            'between', 'among', 'during', 'before', 'after', 'within', 'against', 'toward', 'towards',
            'from', 'to', 'into', 'onto', 'upon', 'across', 'along', 'around', 'behind', 'beside',
            'beyond', 'inside', 'outside', 'throughout', 'underneath', 'up', 'down', 'off', 'out',
            
            # Auxiliary verbs and common verbs
            'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'having',
            'do', 'does', 'did', 'doing', 'will', 'would', 'shall', 'should', 'could', 'can',
            'may', 'might', 'must', 'ought', 'need', 'dare', 'used',
            
            # Common verbs that don't represent specific concepts
            'get', 'got', 'getting', 'give', 'given', 'giving', 'go', 'goes', 'going', 'went', 'gone',
            'come', 'came', 'coming', 'take', 'took', 'taken', 'taking', 'make', 'made', 'making',
            'put', 'putting', 'say', 'said', 'saying', 'see', 'saw', 'seen', 'seeing', 'know', 'knew',
            'known', 'knowing', 'think', 'thought', 'thinking', 'look', 'looked', 'looking',
            'want', 'wanted', 'wanting', 'use', 'used', 'using', 'find', 'found', 'finding',
            'work', 'worked', 'working', 'call', 'called', 'calling', 'try', 'tried', 'trying',
            'ask', 'asked', 'asking', 'feel', 'felt', 'feeling', 'leave', 'left', 'leaving',
            'move', 'moved', 'moving', 'play', 'played', 'playing', 'ran', 'running',
            'turn', 'turned', 'turning', 'start', 'started', 'starting', 'show', 'showed', 'showing',
            'hear', 'heard', 'hearing', 'let', 'letting', 'help', 'helped', 'helping',
            'keep', 'kept', 'keeping', 'begin', 'began', 'beginning', 'seem', 'seemed', 'seeming',
            'open', 'opened', 'opening', 'write', 'wrote', 'written', 'writing', 'sit', 'sat', 'sitting',
            'stand', 'stood', 'standing', 'lose', 'lost', 'losing', 'pay', 'paid', 'paying',
            'meet', 'met', 'meeting', 'include', 'included', 'including', 'continue', 'continued', 'continuing',
            'set', 'setting', 'learn', 'learned', 'learning', 'change', 'changed', 'changing',
            'lead', 'led', 'leading', 'understand', 'understood', 'understanding', 'watch', 'watched', 'watching',
            'follow', 'followed', 'following', 'stop', 'stopped', 'stopping', 'create', 'created', 'creating',
            'speak', 'spoke', 'spoken', 'speaking', 'read', 'reading', 'allow', 'allowed', 'allowing',
            'add', 'added', 'adding', 'spend', 'spent', 'spending', 'grow', 'grew', 'grown', 'growing',
            'happen', 'happened', 'happening', 'tell', 'told', 'telling', 'buy', 'bought', 'buying',
            'provide', 'provided', 'providing', 'serve', 'served', 'serving', 'die', 'died', 'dying',
            'send', 'sent', 'sending', 'expect', 'expected', 'expecting', 'build', 'built', 'building',
            'stay', 'stayed', 'staying', 'fall', 'fell', 'fallen', 'falling', 'cut', 'cutting',
            'reach', 'reached', 'reaching', 'kill', 'killed', 'killing', 'remain', 'remained', 'remaining',
            
            # Adverbs that don't represent specific concepts
            'not', 'no', 'yes', 'well', 'also', 'just', 'now', 'then', 'here', 'there', 'where',
            'when', 'how', 'why', 'very', 'too', 'so', 'more', 'most', 'much', 'many', 'few',
            'little', 'less', 'least', 'only', 'even', 'still', 'already', 'yet', 'again',
            'back', 'away', 'down', 'up', 'out', 'off', 'over', 'under', 'never', 'always',
            'sometimes', 'often', 'usually', 'quite', 'rather', 'really', 'actually', 'probably',
            'maybe', 'perhaps', 'almost', 'nearly', 'about', 'around', 'approximately',
            'especially', 'particularly', 'generally', 'specifically', 'exactly', 'certainly',
            'definitely', 'absolutely', 'completely', 'totally', 'entirely', 'fully',
            'clearly', 'obviously', 'apparently', 'presumably', 'supposedly', 'allegedly',
            'basically', 'essentially', 'fundamentally', 'primarily', 'mainly', 'mostly',
            'largely', 'greatly', 'highly', 'extremely', 'incredibly', 'remarkably',
            'significantly', 'considerably', 'substantially', 'relatively', 'comparatively',
            'accordingly', 'consequently', 'therefore', 'thus', 'hence', 'however',
            'nevertheless', 'nonetheless', 'furthermore', 'moreover', 'additionally',
            'alternatively', 'otherwise', 'meanwhile', 'subsequently', 'previously',
            'recently', 'currently', 'presently', 'immediately', 'instantly', 'suddenly',
            'gradually', 'slowly', 'quickly', 'rapidly', 'easily', 'simply', 'directly',
            
            # Other common non-specific words
            'some', 'any', 'all', 'both', 'each', 'every', 'either', 'neither', 'none',
            'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten',
            'first', 'second', 'third', 'last', 'next', 'previous', 'same', 'different',
            'new', 'old', 'young', 'small', 'large', 'little', 'long', 'short',
            'low', 'good', 'bad', 'right', 'wrong', 'true', 'false', 'real',
            'important', 'possible', 'necessary', 'available', 'sure', 'certain',
            'own', 'other', 'another', 'such', 'way', 'ways', 'thing', 'things',
            'something', 'anything', 'nothing', 'everything', 'someone', 'anyone',
            'everyone', 'nobody', 'everybody', 'somewhere', 'anywhere', 'everywhere',
            'nowhere', 'sometime', 'anytime', 'everytime',
            
            # Technical document filler words
            'example', 'examples', 'case', 'cases', 'section', 'sections', 'chapter', 'chapters',
            'figure', 'figures', 'table', 'tables', 'page', 'pages', 'part', 'parts',
            'note', 'notes', 'see', 'also', 'above', 'below', 'following', 'previous',
            'shown', 'described', 'mentioned', 'referred', 'reference', 'references',
            'documents', 'text', 'content', 'information', 'details', 'description',
            'explanation', 'overview', 'summary', 'conclusion', 'introduction', 'background',
            'purpose', 'objective', 'goal', 'result', 'results', 'outcome', 'outcomes',
            'issue', 'issues', 'problem', 'problems', 'solution', 'solutions', 'approach',
            'method', 'methods', 'technique', 'techniques', 'procedure', 'procedures',
            'step', 'steps', 'process', 'processes', 'operation', 'operations',
        }
        
        # Technical abbreviations and common acronyms that should be kept
        self.technical_terms = {
            'api', 'apis', 'sdk', 'sdks', 'ide', 'ides', 'gui', 'guis', 'cli', 'clis',
            'http', 'https', 'ftp', 'ssh', 'ssl', 'tls', 'tcp', 'udp', 'ip', 'dns',
            'url', 'urls', 'uri', 'uris', 'html', 'css', 'js', 'xml', 'json', 'yaml',
            'sql', 'nosql', 'rest', 'soap', 'crud', 'mvc', 'mvp', 'mvvm', 'orm',
            'cpu', 'gpu', 'ram', 'rom', 'ssd', 'hdd', 'usb', 'pci', 'bios', 'uefi',
            'os', 'vm', 'vms', 'container', 'containers', 'docker', 'kubernetes',
            'aws', 'azure', 'gcp', 'saas', 'paas', 'iaas', 'cd', 'ci', 'devops',
            'ai', 'ml',  # Machine Learning and Artificial Intelligence
        }
    
    def extract_significant_words(self, text: str, min_length: int = 2, max_length: int = 50) -> List[str]:
        """
        Extract significant words from text suitable for technical indexing.
        
        Args:
            text: Input text to analyze
            min_length: Minimum word length to consider
            max_length: Maximum word length to consider
            
        Returns:
            List of significant words in lowercase
        """
        if not text:
            return []
        
        # Convert to lowercase and extract words
        words = re.findall(r'\b[a-zA-Z]+(?:[_-][a-zA-Z]+)*\b', text.lower())
        
        significant_words = []
        
        for word in words:
            # Skip if too short or too long
            if len(word) < min_length or len(word) > max_length:
                continue
            
            # Keep technical terms even if they're in stop words
            if word in self.technical_terms:
                significant_words.append(word)
                continue
            
            # Skip stop words
            if word in self.stop_words:
                continue
            
            # Skip pure numbers
            if word.isdigit():
                continue
            
            # Skip words that are mostly numbers
            if sum(c.isdigit() for c in word) > len(word) * 0.7:
                continue
            
            # Keep words that start with capital letters in original text
            # (likely proper nouns or technical terms)
            original_word_pattern = r'\b' + re.escape(word) + r'\b'
            if re.search(original_word_pattern, text, re.IGNORECASE):
                # Check if it appears capitalized in the original
                capitalized_pattern = r'\b' + word[0].upper() + re.escape(word[1:]) + r'\b'
                if re.search(capitalized_pattern, text):
                    significant_words.append(word)
                    continue
            
            # Keep words that contain technical patterns
            if self._is_technical_word(word):
                significant_words.append(word)
                continue
            
            # Keep words with specific suffixes that indicate technical terms
            technical_suffixes = [
                'tion', 'sion', 'ness', 'ment', 'ity', 'ty', 'ism', 'ist',
                'ing', 'er', 'or', 'ar', 'al', 'ic', 'ical', 'ous', 'ious',
                'ful', 'less', 'able', 'ible', 'ive', 'ative', 'itive',
                'ware', 'soft', 'tech', 'system', 'frame', 'protocol',
                'engine', 'server', 'client', 'service', 'driver', 'handler'
            ]
            
            if any(word.endswith(suffix) for suffix in technical_suffixes):
                significant_words.append(word)
                continue
            
            # Keep compound words (with hyphens or underscores)
            if '_' in word or '-' in word:
                significant_words.append(word)
                continue
            
            # Keep words that are likely domain-specific terms
            # (3+ characters, not in common stop words)
            if len(word) >= 3:
                significant_words.append(word)
        
        return significant_words
    
    def _is_technical_word(self, word: str) -> bool:
        """Check if a word follows technical naming patterns."""
        
        # Programming language keywords and common technical terms
        programming_terms = {
            'class', 'function', 'method', 'variable', 'constant', 'parameter',
            'argument', 'return', 'void', 'int', 'string', 'boolean', 'array',
            'list', 'dict', 'map', 'set', 'tuple', 'object', 'instance',
            'interface', 'abstract', 'static', 'public', 'private', 'protected',
            'virtual', 'override', 'inherit', 'extend', 'implement', 'import',
            'export', 'module', 'package', 'library', 'framework', 'namespace',
            'thread', 'process', 'async', 'sync', 'callback', 'event', 'handler',
            'listener', 'observer', 'pattern', 'singleton', 'factory', 'builder',
            'adapter', 'facade', 'proxy', 'decorator', 'strategy', 'command',
            'iterator', 'template', 'generic', 'exception', 'error', 'debug',
            'test', 'unit', 'integration', 'mock', 'stub', 'fixture', 'assert',
            'validate', 'serialize', 'deserialize', 'encode', 'decode', 'parse',
            'compile', 'runtime', 'garbage', 'collector', 'memory', 'heap', 'stack',
            'buffer', 'cache', 'database', 'query', 'index', 'transaction',
            'commit', 'rollback', 'schema', 'table', 'column', 'row', 'record',
            'primary', 'foreign', 'key', 'constraint', 'trigger', 'procedure',
            'algorithm', 'complexity', 'optimization', 'performance', 'scalability',
            'security', 'authentication', 'authorization', 'encryption', 'hash',
            'token', 'session', 'cookie', 'header', 'request', 'response',
            'endpoint', 'route', 'middleware', 'pipeline', 'queue', 'worker',
            'scheduler', 'daemon', 'service', 'microservice', 'monolith',
            'container', 'orchestration', 'deployment', 'configuration', 'environment',
            'production', 'development', 'staging', 'testing', 'debugging',
            'logging', 'monitoring', 'metrics', 'analytics', 'reporting'
        }
        
        if word in programming_terms:
            return True
        
        # Check for technical patterns
        # CamelCase or snake_case patterns
        if '_' in word or any(c.isupper() for c in word[1:]):
            return True
        
        # File extensions
        if word.startswith('.') and len(word) > 1:
            return True
        
        # Version numbers or technical identifiers
        if re.match(r'^v?\d+(\.\d+)*[a-z]*$', word):
            return True
        
        # Technical abbreviations (all caps, 2-6 characters)
        if word.isupper() and 2 <= len(word) <= 6:
            return True
        
        return False
    
    def get_word_frequency(self, texts: List[str], min_frequency: int = 2) -> Dict[str, int]:
        """
        Get frequency count of significant words across multiple texts.
        
        Args:
            texts: List of text strings to analyze
            min_frequency: Minimum frequency to include word in results
            
        Returns:
            Dictionary mapping words to their frequency counts
        """
        all_words = []
        
        for text in texts:
            words = self.extract_significant_words(text)
            all_words.extend(words)
        
        # Count frequencies
        word_counts = Counter(all_words)
        
        # Filter by minimum frequency
        return {word: count for word, count in word_counts.items() 
                if count >= min_frequency}
    
    def consolidate_word_variations(self, word_to_files: Dict[str, List[str]], max_combined: int = 24) -> Dict[str, Dict]:
        """
        Consolidate word variations using regex patterns (R-WORD-014, R-WORD-015).
        
        Args:
            word_to_files: Mapping of words to files containing them
            max_combined: Maximum combined matches to allow consolidation
            
        Returns:
            Dictionary mapping consolidated patterns to word groups and files
        """
        consolidated = {}
        used_words = set()
        all_words = list(word_to_files.keys())
        
        # Process each word to find its variations
        for base_word in all_words:
            if base_word in used_words:
                continue
                
            variations_found = {base_word: word_to_files[base_word]}
            
            # Check for plural forms: sdk -> sdks, apis -> api
            if not base_word.endswith('s') and len(base_word) >= 3:
                plural_form = base_word + 's'
                if plural_form in word_to_files and plural_form not in used_words:
                    # Check if combined files count is reasonable
                    total_files = set(word_to_files[base_word])
                    total_files.update(word_to_files[plural_form])
                    if len(total_files) <= max_combined:
                        variations_found[plural_form] = word_to_files[plural_form]
            
            # Check for base forms: sdks -> sdk, apis -> api
            if base_word.endswith('s') and len(base_word) > 3 and not base_word.endswith(('ss', 'us', 'is')):
                base_form = base_word[:-1]
                if base_form in word_to_files and base_form not in used_words:
                    # Check if combined files count is reasonable
                    total_files = set(word_to_files[base_word])
                    total_files.update(word_to_files[base_form])
                    if len(total_files) <= max_combined:
                        variations_found[base_form] = word_to_files[base_form]
            
            # Check for verb forms: process -> processing/processed
            for other_word in all_words:
                if (other_word != base_word and 
                    other_word not in used_words and
                    other_word not in variations_found):
                    
                    # Check if one is a variation of the other
                    if self._are_word_variations(base_word, other_word):
                        total_files = set(word_to_files[base_word])
                        total_files.update(word_to_files[other_word])
                        if len(total_files) <= max_combined:
                            variations_found[other_word] = word_to_files[other_word]
            
            # If we found variations, create consolidated entry
            if len(variations_found) > 1:
                # Create pattern name - use shortest word as base with regex
                base_for_pattern = min(variations_found.keys(), key=len)
                
                # Check the type of variations to create appropriate pattern
                words = list(variations_found.keys())
                if any(w.endswith('s') for w in words) and any(not w.endswith('s') for w in words):
                    # Plural variations
                    base_root = base_for_pattern.rstrip('s')
                    pattern_name = f"{base_root}s?"
                elif any(w.endswith(('ing', 'ed', 'er', 'tion', 'sion', 'ment')) for w in words):
                    # Verb/suffix variations  
                    base_root = self._extract_root_word(words)
                    pattern_name = f"{base_root}.*"
                else:
                    # Other variations
                    pattern_name = f"{base_for_pattern}.*"
                
                # Combine all files
                all_files = set()
                for word_files in variations_found.values():
                    all_files.update(word_files)
                
                consolidated[pattern_name] = {
                    'words': words,
                    'files': list(all_files),
                    'is_consolidated': True
                }
                
                # Mark all words as used
                used_words.update(words)
            else:
                # No variations found, keep original
                if base_word not in used_words:
                    consolidated[base_word] = {
                        'words': [base_word],
                        'files': word_to_files[base_word],
                        'is_consolidated': False
                    }
                    used_words.add(base_word)
        
        return consolidated
    
    def _are_word_variations(self, word1: str, word2: str) -> bool:
        """Check if two words are variations of each other."""
        # Check for common suffix variations
        suffixes = ['ing', 'ed', 'er', 'est', 'ly', 'tion', 'sion', 'ment', 'ful', 'less', 'able', 'ible']
        
        for suffix in suffixes:
            if word1.endswith(suffix) and word2 == word1[:-len(suffix)]:
                return True
            if word2.endswith(suffix) and word1 == word2[:-len(suffix)]:
                return True
        
        return False
    
    def _extract_root_word(self, words: List[str]) -> str:
        """Extract the common root from a list of word variations."""
        if not words:
            return ""
        
        # Find the shortest word as potential root
        shortest = min(words, key=len)
        
        # Check if shortest word is a root for others
        for word in words:
            if word != shortest and not word.startswith(shortest):
                # Try removing common suffixes to find root
                for suffix in ['ing', 'ed', 'er', 'tion', 'sion', 'ment']:
                    if word.endswith(suffix):
                        potential_root = word[:-len(suffix)]
                        if len(potential_root) >= 3:
                            return potential_root
        
        return shortest
    
    def create_hierarchical_groups(self, words: List[str], max_children: int = 24) -> Dict:
        """
        Create hierarchical groupings of words to limit children per node.
        
        Args:
            words: Sorted list of words to group
            max_children: Maximum number of children per node
            
        Returns:
            Hierarchical dictionary structure for word groupings
        """
        if len(words) <= max_children:
            # Base case: small enough to be direct children
            return {'words': words}
        
        # Group words by first character
        char_groups = {}
        for word in words:
            first_char = word[0].lower()
            if first_char not in char_groups:
                char_groups[first_char] = []
            char_groups[first_char].append(word)
        
        # If we have few enough character groups, handle them intelligently
        if len(char_groups) <= max_children:
            result = {}
            for char, char_words in char_groups.items():
                if len(char_words) == 1:
                    # R-WORD-016: Single word - add directly without character grouping
                    word = char_words[0]
                    result[word] = {'words': [word]}
                elif len(char_words) <= max_children:
                    # Small group - check if we really need character grouping
                    if len(char_groups) == 1:
                        # Only one character group, so flatten completely
                        for word in char_words:
                            result[word] = {'words': [word]}
                    else:
                        # Multiple character groups, so group by character is useful
                        result[char] = {'words': char_words}
                else:
                    # Need to subdivide this character group
                    subdivided = self._subdivide_character_group(char_words, max_children)
                    if 'words' in subdivided and len(subdivided['words']) == len(char_words):
                        # Subdivision didn't help, just put words directly
                        for word in char_words:
                            result[word] = {'words': [word]}
                    else:
                        # Merge subdivided groups directly to avoid redundant character nesting
                        result.update(subdivided)
            return result
        
        # Too many character groups, need to combine some
        return self._combine_character_groups(char_groups, max_children)
    
    def _subdivide_character_group(self, words: List[str], max_children: int) -> Dict:
        """Subdivide a character group by prefixes."""
        if len(words) <= max_children:
            return {'words': words}
        
        # Group by 2-character prefixes, but handle single-letter words specially
        prefix_groups = {}
        single_char_words = []
        
        for word in words:
            if len(word) == 1:
                # Single character words go directly to avoid redundant grouping
                single_char_words.append(word)
            else:
                prefix = word[:2].lower()
                if prefix not in prefix_groups:
                    prefix_groups[prefix] = []
                prefix_groups[prefix].append(word)
        
        # If we have single character words and they fit within limits, add them directly
        result = {}
        for word in single_char_words:
            result[word] = {'words': [word]}
        
        # If adding single words would exceed max_children, we need to group them
        remaining_slots = max_children - len(result)
        if remaining_slots <= 0 and single_char_words:
            # No room for individual single chars, must group them
            if len(single_char_words) == 1:
                # Just one single char word - add it directly anyway
                result[single_char_words[0]] = {'words': single_char_words}
            else:
                # Multiple single chars - group them under a range
                first_char = min(single_char_words)[0].lower()
                last_char = max(single_char_words)[0].lower()
                if first_char == last_char:
                    result[first_char] = {'words': single_char_words}
                else:
                    result[f"{first_char}-{last_char}"] = {'words': single_char_words}
        
        # Handle the multi-character word prefixes
        if len(prefix_groups) > remaining_slots:
            # Too many prefix groups, need to combine them
            combined_prefixes = self._combine_prefix_groups(prefix_groups, remaining_slots)
            result.update(combined_prefixes)
        else:
            # Process each prefix group
            for prefix, prefix_words in prefix_groups.items():
                if len(prefix_words) <= max_children:
                    result[prefix] = {'words': prefix_words}
                else:
                    # Further subdivision needed (3-character prefixes)
                    result[prefix] = self._subdivide_by_longer_prefix(prefix_words, max_children)
        
        return result
    
    def _combine_character_groups(self, char_groups: Dict[str, List[str]], max_children: int) -> Dict:
        """Combine character groups into ranges."""
        chars = sorted(char_groups.keys())
        result = {}
        
        i = 0
        while i < len(chars):
            # Determine how many characters to group together
            remaining_chars = len(chars) - i
            remaining_slots = max_children - len([k for k in result.keys()])
            
            if remaining_chars <= remaining_slots:
                # Remaining characters can fit in available slots
                group_size = 1
            else:
                # Need to group characters together
                import math
                group_size = math.ceil(remaining_chars / remaining_slots)
            
            # Create character range
            end_idx = min(i + group_size, len(chars))
            group_chars = chars[i:end_idx]
            
            if len(group_chars) == 1:
                range_label = group_chars[0]
            else:
                range_label = f"{group_chars[0]}-{group_chars[-1]}"
            
            # Combine words from all characters in this range
            range_words = []
            for char in group_chars:
                range_words.extend(char_groups[char])
            
            # Recursively organize this range
            result[range_label] = self.create_hierarchical_groups(sorted(range_words), max_children)
            
            i = end_idx
        
        return result
    
    def _combine_prefix_groups(self, prefix_groups: Dict[str, List[str]], max_children: int) -> Dict:
        """Combine prefix groups into ranges."""
        prefixes = sorted(prefix_groups.keys())
        result = {}
        
        # Calculate how many prefixes per group
        import math
        group_size = max(1, math.ceil(len(prefixes) / max_children))
        
        i = 0
        while i < len(prefixes):
            end_idx = min(i + group_size, len(prefixes))
            group_prefixes = prefixes[i:end_idx]
            
            if len(group_prefixes) == 1:
                range_label = group_prefixes[0]
            else:
                range_label = f"{group_prefixes[0]}-{group_prefixes[-1]}"
            
            # Combine words from all prefixes in this range
            range_words = []
            for prefix in group_prefixes:
                range_words.extend(prefix_groups[prefix])
            
            result[range_label] = {'words': sorted(range_words)}
            i = end_idx
        
        return result
    
    def _subdivide_by_longer_prefix(self, words: List[str], max_children: int) -> Dict:
        """Subdivide by 3+ character prefixes."""
        # Group by 3-character prefixes
        prefix_groups = {}
        for word in words:
            prefix = word[:3].lower() if len(word) >= 3 else word.lower()
            if prefix not in prefix_groups:
                prefix_groups[prefix] = []
            prefix_groups[prefix].append(word)
        
        if len(prefix_groups) <= max_children:
            return {prefix: {'words': words} for prefix, words in prefix_groups.items()}
        
        # If still too many, just split alphabetically
        words_per_group = max(1, len(words) // max_children)
        result = {}
        
        for i in range(0, len(words), words_per_group):
            group_words = words[i:i + words_per_group]
            if group_words:
                first_word = group_words[0]
                last_word = group_words[-1]
                
                if len(group_words) == 1:
                    label = first_word
                else:
                    # Create range label from first few characters
                    first_prefix = first_word[:3] if len(first_word) >= 3 else first_word
                    last_prefix = last_word[:3] if len(last_word) >= 3 else last_word
                    if first_prefix == last_prefix:
                        label = first_prefix
                    else:
                        label = f"{first_prefix}-{last_prefix}"
                
                result[label] = {'words': group_words}
        
        return result