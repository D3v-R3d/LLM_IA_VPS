"""
Tool Working Memory

Persistent memory for agent tool execution.
Stores discovered paths, files, tool health, and notes in tool.md
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class ToolMemory:
    """
    Working memory for agent tool execution.
    
    Automatically persists to tool.md and reloads on next run.
    """
    # Limits
    MAX_PATHS = 20
    MAX_FILES = 20
    MAX_TESTS = 20
    MAX_NOTES = 20
    
    # Storage
    known_paths: List[str] = field(default_factory=list)
    known_files: List[str] = field(default_factory=list)
    tool_health: Dict[str, str] = field(default_factory=dict)
    recent_tests: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)
    
    # File path
    memory_file: str = "/home/projects/tower_project/tool.md"
    
    def load(self) -> Dict:
        """
        Load memory from tool.md
        Returns dict representation
        """
        try:
            if not os.path.exists(self.memory_file):
                # Create empty file if not exists
                self.save({})
                return self._to_dict()
            
            with open(self.memory_file, "r", encoding="utf-8") as f:
                content = f.read()
            
            # Parse markdown sections
            self._parse_markdown(content)
            return self._to_dict()
            
        except Exception as e:
            # If parse fails, start fresh
            self.known_paths = []
            self.known_files = []
            self.tool_health = {}
            self.recent_tests = []
            self.notes = []
            return self._to_dict()
    
    def save(self, memory: Optional[Dict] = None):
        """
        Save memory to tool.md
        """
        # Update from dict only if provided and non-empty
        if memory:
            self._from_dict(memory)
        
        # Render markdown
        markdown = self._render_markdown()
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(self.memory_file), exist_ok=True)
        
        # Write file
        with open(self.memory_file, "w", encoding="utf-8") as f:
            f.write(markdown)
    
    def update(
        self,
        tool_results: List[Any],
        user_message: str,
        final_response: str
    ):
        """
        Update memory with new information from tool execution.
        
        Extracts:
        - Paths from tool results
        - Files from tool results
        - Tool health (success/failed)
        - Business notes
        """
        # Extract paths
        for result in tool_results:
            if hasattr(result, 'tool'):
                tool_name = result.tool
                success = result.success if hasattr(result, 'success') else False
                
                # Tool health
                self.tool_health[tool_name] = "ok" if success else "failed"
                
                # Extract paths from data/summary
                if hasattr(result, 'data') and result.data:
                    data = result.data
                    if isinstance(data, dict):
                        # Look for path fields
                        for key in ['path', 'file_path', 'directory', 'folder']:
                            if key in data and data[key]:
                                self._add_path(str(data[key]))
                        
                        # Look for files list
                        if 'files' in data and isinstance(data['files'], list):
                            for f in data['files']:
                                if isinstance(f, str):
                                    self._add_file(f)
                        
                        # Look for content with paths
                        if 'content' in data and isinstance(data['content'], str):
                            self._extract_paths_from_text(data['content'])
                
                if hasattr(result, 'summary') and result.summary:
                    self._extract_paths_from_text(result.summary)
        
        # Extract business notes
        self._extract_notes(user_message, final_response, tool_results)
        
        # Add test record
        if tool_results:
            test_summary = self._summarize_test(tool_results)
            if test_summary:
                self._add_test(test_summary)
        
        # Enforce limits (FIFO)
        self._enforce_limits()
        
        # Save to file
        self.save({})
    
    def render(self) -> str:
        """
        Render memory as compact text for LLM context.
        Max 500 chars.
        """
        parts = []
        
        if self.known_paths:
            parts.append(f"Known paths: {', '.join(self.known_paths[-5:])}")
        
        if self.known_files:
            parts.append(f"Known files: {', '.join(self.known_files[-5:])}")
        
        if self.tool_health:
            health_str = ', '.join(f"{k}={v}" for k, v in list(self.tool_health.items())[-5:])
            parts.append(f"Tool health: {health_str}")
        
        if self.recent_tests:
            parts.append(f"Recent tests: {', '.join(self.recent_tests[-3:])}")
        
        if self.notes:
            parts.append(f"Notes: {', '.join(self.notes[-3:])}")
        
        result = '\n'.join(parts)
        
        # Truncate to 500 chars if needed
        if len(result) > 500:
            result = result[:497] + "..."
        
        return result
    
    def _parse_markdown(self, content: str):
        """Parse markdown content into memory fields."""
        # Reset
        self.known_paths = []
        self.known_files = []
        self.tool_health = {}
        self.recent_tests = []
        self.notes = []
        
        current_section = None
        
        for line in content.split('\n'):
            line = line.strip()
            
            if line.startswith('## '):
                section = line[3:].lower()
                if 'path' in section:
                    current_section = 'paths'
                elif 'file' in section and 'known' in section:
                    current_section = 'files'
                elif 'health' in section:
                    current_section = 'health'
                elif 'test' in section:
                    current_section = 'tests'
                elif 'note' in section:
                    current_section = 'notes'
                else:
                    current_section = None
            
            elif line.startswith('- ') and current_section:
                item = line[2:].strip()
                
                if current_section == 'paths':
                    self.known_paths.append(item)
                elif current_section == 'files':
                    self.known_files.append(item)
                elif current_section == 'health':
                    if ':' in item:
                        key, value = item.split(':', 1)
                        self.tool_health[key.strip()] = value.strip()
                    elif '=' in item:
                        key, value = item.split('=', 1)
                        self.tool_health[key.strip()] = value.strip()
                elif current_section == 'tests':
                    self.recent_tests.append(item)
                elif current_section == 'notes':
                    self.notes.append(item)
    
    def _to_dict(self) -> Dict:
        """Convert to dict representation."""
        return {
            'known_paths': self.known_paths,
            'known_files': self.known_files,
            'tool_health': self.tool_health,
            'recent_tests': self.recent_tests,
            'notes': self.notes,
        }
    
    def _from_dict(self, data: Dict):
        """Load from dict representation."""
        if 'known_paths' in data:
            self.known_paths = data['known_paths']
        if 'known_files' in data:
            self.known_files = data['known_files']
        if 'tool_health' in data:
            self.tool_health = data['tool_health']
        if 'recent_tests' in data:
            self.recent_tests = data['recent_tests']
        if 'notes' in data:
            self.notes = data['notes']
    
    def _render_markdown(self) -> str:
        """Render memory as markdown."""
        lines = ["# Tool Working Memory", ""]
        
        # Known Paths
        lines.append("## Known Paths")
        for path in self.known_paths:
            lines.append(f"- {path}")
        if not self.known_paths:
            lines.append("- _none_")
        lines.append("")
        
        # Known Files
        lines.append("## Known Files")
        for f in self.known_files:
            lines.append(f"- {f}")
        if not self.known_files:
            lines.append("- _none_")
        lines.append("")
        
        # Tool Health
        lines.append("## Tool Health")
        for tool, status in self.tool_health.items():
            lines.append(f"- {tool}: {status}")
        if not self.tool_health:
            lines.append("- _none_")
        lines.append("")
        
        # Recent Tests
        lines.append("## Recent Tests")
        for test in self.recent_tests:
            lines.append(f"- {test}")
        if not self.recent_tests:
            lines.append("- _none_")
        lines.append("")
        
        # Notes
        lines.append("## Notes")
        for note in self.notes:
            lines.append(f"- {note}")
        if not self.notes:
            lines.append("- _none_")
        
        return '\n'.join(lines)
    
    def _add_path(self, path: str):
        """Add a path with deduplication."""
        # Normalize path
        path = path.strip()
        if not path:
            return
        
        # Skip if already exists
        if path in self.known_paths:
            return
        
        # Validate looks like a path
        if not (path.startswith('/') or '/' in path):
            return
        
        self.known_paths.append(path)
    
    def _add_file(self, filename: str):
        """Add a file with deduplication."""
        filename = filename.strip()
        if not filename:
            return
        
        if filename in self.known_files:
            return
        
        # Validate has extension
        if '.' not in os.path.basename(filename):
            return
        
        self.known_files.append(filename)
    
    def _add_test(self, test_summary: str):
        """Add a test record."""
        if not test_summary:
            return
        
        if test_summary in self.recent_tests:
            return
        
        self.recent_tests.append(test_summary)
    
    def _extract_paths_from_text(self, text: str):
        """Extract paths from text content."""
        if not text:
            return
        
        # Unix-style absolute paths
        path_pattern = r"(/[A-Za-z0-9_\-./]+)"
        matches = re.findall(path_pattern, text)
        for match in matches:
            if len(match) > 3:  # Skip short paths like /a
                self._add_path(match)
        
        # File extensions
        file_extensions = ['.yaml', '.json', '.py', '.txt', '.pdf', '.mp4', '.jpg', '.png', '.mkv', '.avi']
        for ext in file_extensions:
            ext_pattern = rf"([A-Za-z0-9_\-]+{ext})"
            matches = re.findall(ext_pattern, text, re.IGNORECASE)
            for match in matches:
                self._add_file(match)
    
    def _extract_notes(self, user_message: str, final_response: str, tool_results: List):
        """Extract business notes from execution."""
        # Check for content type mentions
        content_keywords = {
            'film': 'NAS contains movies',
            'movie': 'NAS contains movies',
            'photo': 'NAS contains images',
            'image': 'NAS contains images',
            'picture': 'NAS contains images',
            'music': 'NAS contains music',
            'song': 'NAS contains music',
            'document': 'NAS contains documents',
            'pdf': 'NAS contains PDF documents',
        }
        
        text = (user_message + " " + final_response).lower()
        
        for keyword, note in content_keywords.items():
            if keyword in text and note not in self.notes:
                self.notes.append(note)
        
        # Check for successful tool discoveries
        for result in tool_results:
            if hasattr(result, 'success') and result.success:
                tool_name = getattr(result, 'tool', '')
                
                # NAS success = note about NAS working
                if 'nas' in tool_name.lower():
                    note = f"{tool_name} works"
                    if note not in self.notes:
                        self.notes.append(note)
    
    def _summarize_test(self, tool_results: List) -> str:
        """Create test summary from results."""
        if not tool_results:
            return None
        
        summaries = []
        for result in tool_results:
            if hasattr(result, 'tool'):
                tool_name = result.tool
                success = getattr(result, 'success', False)
                status = "success" if success else "failed"
                summaries.append(f"{tool_name} {status}")
        
        return '; '.join(summaries) if summaries else None
    
    def _enforce_limits(self):
        """Enforce FIFO limits on all lists."""
        # Paths
        if len(self.known_paths) > self.MAX_PATHS:
            self.known_paths = self.known_paths[-self.MAX_PATHS:]
        
        # Files
        if len(self.known_files) > self.MAX_FILES:
            self.known_files = self.known_files[-self.MAX_FILES:]
        
        # Tests
        if len(self.recent_tests) > self.MAX_TESTS:
            self.recent_tests = self.recent_tests[-self.MAX_TESTS:]
        
        # Notes
        if len(self.notes) > self.MAX_NOTES:
            self.notes = self.notes[-self.MAX_NOTES:]
        
        # Tool health (keep last 20)
        if len(self.tool_health) > self.MAX_PATHS:
            # Keep most recent (last inserted)
            items = list(self.tool_health.items())[-self.MAX_PATHS:]
            self.tool_health = dict(items)


# Global instance
_tool_memory: Optional[ToolMemory] = None


def get_tool_memory() -> ToolMemory:
    """Get or create global ToolMemory instance."""
    global _tool_memory
    if _tool_memory is None:
        _tool_memory = ToolMemory()
        _tool_memory.load()
    return _tool_memory


def reset_tool_memory():
    """Reset global instance (for testing)."""
    global _tool_memory
    _tool_memory = None
