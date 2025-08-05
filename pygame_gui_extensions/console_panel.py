import pygame
import pygame_gui
from pygame_gui.core import UIElement, ObjectID
from pygame_gui.core.interfaces import IContainerLikeInterface
from typing import List, Optional, Dict, Any, Union, Callable, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum
import re
import sys
import io
import traceback
import time
import keyword
import builtins
from contextlib import redirect_stdout, redirect_stderr

try:
    from pygame_gui.core.interfaces.gui_font_interface import IGUIFontInterface
except ImportError:
    IGUIFontInterface = None

CONSOLE_DEBUG = False

# Define custom pygame-gui events
UI_CONSOLE_COMMAND_EXECUTED = pygame.USEREVENT + 200
UI_CONSOLE_OUTPUT_ADDED = pygame.USEREVENT + 201
UI_CONSOLE_HISTORY_CHANGED = pygame.USEREVENT + 202
UI_CONSOLE_CLEAR_REQUESTED = pygame.USEREVENT + 203
UI_CONSOLE_SCROLL_CHANGED = pygame.USEREVENT + 204
UI_CONSOLE_COMPLETION_REQUESTED = pygame.USEREVENT + 205
UI_CONSOLE_THEME_CHANGED = pygame.USEREVENT + 206
UI_CONSOLE_FILTER_CHANGED = pygame.USEREVENT + 207
UI_CONSOLE_MACRO_EXECUTED = pygame.USEREVENT + 208


class ConsoleOutputType(Enum):
    """Types of console output"""
    COMMAND = "command"
    RESULT = "result"
    ERROR = "error"
    INFO = "info"
    WARNING = "warning"
    DEBUG = "debug"
    SYSTEM = "system"


class ConsoleMode(Enum):
    """Console operation modes"""
    PYTHON = "python"
    SHELL = "shell"
    CUSTOM = "custom"


class ConsoleSyntaxTheme(Enum):
    """Syntax highlighting themes"""
    DARK = "dark"
    LIGHT = "light"
    MONOKAI = "monokai"
    SOLARIZED_DARK = "solarized_dark"
    SOLARIZED_LIGHT = "solarized_light"


@dataclass
class ConsoleLayoutConfig:
    """Layout and spacing configuration for console panel"""
    # Panel dimensions
    input_height: int = 30
    output_line_height: int = 16
    scrollbar_width: int = 20

    # Margins and padding
    panel_padding: int = 8
    input_padding: int = 6
    output_padding: int = 4
    prompt_spacing: int = 8

    # Visual elements
    border_width: int = 1
    focus_border_width: int = 2
    cursor_width: int = 2
    selection_alpha: int = 128

    # Scrolling
    scroll_speed: int = 3
    page_scroll_lines: int = 10
    auto_scroll_threshold: int = 5

    # Text rendering
    tab_size: int = 4
    line_number_width: int = 40
    max_output_lines: int = 1000

    # Fallback settings
    fallback_font_size: int = 12


@dataclass
class ConsoleInteractionConfig:
    """Interaction and control configuration"""
    # Keyboard shortcuts
    clear_shortcut: int = pygame.K_l  # Ctrl+L
    history_up: int = pygame.K_UP
    history_down: int = pygame.K_DOWN
    autocomplete_key: int = pygame.K_TAB
    interrupt_key: int = pygame.K_c  # Ctrl+C
    execute_key: int = pygame.K_RETURN
    multiline_key: int = pygame.K_RETURN  # Shift+Return for multiline

    # Mouse interaction
    enable_mouse_selection: bool = True
    enable_context_menu: bool = True
    enable_drag_scroll: bool = True
    double_click_select_word: bool = True
    triple_click_select_line: bool = True

    # Input behavior
    enable_history: bool = True
    enable_autocomplete: bool = True
    enable_syntax_highlighting: bool = True
    enable_bracket_matching: bool = True

    # Key repeat settings
    key_repeat_initial_delay: float = 0.5  # Initial delay before repeating (seconds)
    key_repeat_rate: float = 0.05  # Time between repeats (seconds)
    enable_key_repeat: bool = True  # Enable/disable key repeat

    # Timing
    cursor_blink_rate: float = 0.5
    autocomplete_delay: float = 0.5
    command_timeout: float = 5.0


@dataclass
class ConsoleBehaviorConfig:
    """Behavior and feature configuration"""
    # Command execution
    enable_python_exec: bool = True
    enable_shell_commands: bool = False
    enable_custom_commands: bool = True
    capture_stdout: bool = True
    capture_stderr: bool = True

    # Output management
    auto_scroll_output: bool = True
    preserve_output_on_clear: bool = False
    show_timestamps: bool = False
    show_line_numbers: bool = False
    word_wrap: bool = True

    # History and completion
    max_history_size: int = 100
    save_history_to_file: bool = False
    history_file_path: str = "console_history.txt"
    case_sensitive_completion: bool = False

    # Filtering and search
    enable_output_filtering: bool = True
    filter_case_sensitive: bool = False
    highlight_search_terms: bool = True

    # Security and safety
    restrict_dangerous_commands: bool = True
    confirm_destructive_operations: bool = True
    sandbox_python_execution: bool = False

    # Visual features
    show_welcome_message: bool = True
    show_command_prompt: bool = True
    animate_text_input: bool = False


@dataclass
class ConsoleConfig:
    """Complete configuration for console panel"""
    layout: ConsoleLayoutConfig = field(default_factory=ConsoleLayoutConfig)
    interaction: ConsoleInteractionConfig = field(default_factory=ConsoleInteractionConfig)
    behavior: ConsoleBehaviorConfig = field(default_factory=ConsoleBehaviorConfig)

    # Console settings
    mode: ConsoleMode = ConsoleMode.PYTHON
    syntax_theme: ConsoleSyntaxTheme = ConsoleSyntaxTheme.DARK
    prompt_text: str = ">>> "
    continuation_prompt: str = "... "

    # Custom command handlers
    custom_commands: Dict[str, Callable] = field(default_factory=dict)
    command_aliases: Dict[str, str] = field(default_factory=dict)
    macros: Dict[str, List[str]] = field(default_factory=dict)


@dataclass
class ConsoleOutputEntry:
    """Single console output entry"""
    text: str
    output_type: ConsoleOutputType
    timestamp: float
    line_number: int = 0

    def __post_init__(self):
        if self.timestamp == 0:
            self.timestamp = time.time()


class ConsoleSyntaxHighlighter:
    """Syntax highlighting for console input"""

    def __init__(self, theme: ConsoleSyntaxTheme):
        self.theme = theme
        self._setup_colors()
        self._setup_patterns()

    def _setup_colors(self):
        """Setup color schemes for different themes"""
        if self.theme == ConsoleSyntaxTheme.DARK:
            self.colors = {
                'keyword': pygame.Color(255, 165, 0),  # Orange
                'string': pygame.Color(144, 238, 144),  # Light green
                'comment': pygame.Color(128, 128, 128),  # Gray
                'number': pygame.Color(255, 182, 193),  # Light pink
                'builtin': pygame.Color(173, 216, 230),  # Light blue
                'operator': pygame.Color(255, 255, 255),  # White
                'default': pygame.Color(255, 255, 255)  # White
            }
        elif self.theme == ConsoleSyntaxTheme.LIGHT:
            self.colors = {
                'keyword': pygame.Color(0, 0, 255),  # Blue
                'string': pygame.Color(0, 128, 0),  # Green
                'comment': pygame.Color(128, 128, 128),  # Gray
                'number': pygame.Color(255, 0, 0),  # Red
                'builtin': pygame.Color(128, 0, 128),  # Purple
                'operator': pygame.Color(0, 0, 0),  # Black
                'default': pygame.Color(0, 0, 0)  # Black
            }
        else:
            # Default to dark theme colors
            self._setup_colors_dark()

    def _setup_patterns(self):
        """Setup regex patterns for syntax highlighting"""
        self.patterns = [
            (r'#.*$', 'comment'),  # Comments
            (r'"([^"\\]|\\.)*"', 'string'),  # Double-quoted strings
            (r"'([^'\\]|\\.)*'", 'string'),  # Single-quoted strings
            (r'\b\d+\.?\d*\b', 'number'),  # Numbers
            (r'\b(' + '|'.join(keyword.kwlist) + r')\b', 'keyword'),  # Keywords
            (r'\b(' + '|'.join(dir(builtins)) + r')\b', 'builtin'),  # Builtins
            (r'[+\-*/%=<>!&|^~]', 'operator'),  # Operators
        ]

        # Compile patterns
        self.compiled_patterns = [(re.compile(pattern), token_type)
                                  for pattern, token_type in self.patterns]

    def highlight(self, text: str) -> List[Tuple[str, str]]:
        """Return list of (text_chunk, token_type) tuples"""
        if not text:
            return [('', 'default')]

        tokens = []
        pos = 0

        while pos < len(text):
            matched = False

            # Try each pattern
            for pattern, token_type in self.compiled_patterns:
                match = pattern.match(text, pos)
                if match:
                    # Add any unmatched text before this match
                    if match.start() > pos:
                        tokens.append((text[pos:match.start()], 'default'))

                    # Add the matched text
                    tokens.append((match.group(), token_type))
                    pos = match.end()
                    matched = True
                    break

            if not matched:
                # No pattern matched, advance by one character
                tokens.append((text[pos], 'default'))
                pos += 1

        return tokens


class ConsoleThemeManager:
    """Manages theming for the console panel"""

    def __init__(self, ui_manager: pygame_gui.UIManager, element_ids: List[str]):
        self.ui_manager = ui_manager
        self.element_ids = element_ids
        self.themed_colors = {}
        self.themed_font = None
        self._update_theme_data()

    def _update_theme_data(self):
        """Update theme-dependent data with comprehensive fallbacks"""
        # Default color mappings with fallbacks
        color_mappings = {
            'console_bg': pygame.Color(20, 20, 20),
            'input_bg': pygame.Color(30, 30, 30),
            'output_bg': pygame.Color(25, 25, 25),
            'text': pygame.Color(255, 255, 255),
            'prompt': pygame.Color(0, 255, 0),
            'cursor': pygame.Color(255, 255, 255),
            'selection': pygame.Color(100, 100, 255),
            'border': pygame.Color(80, 80, 80),
            'focus_border': pygame.Color(120, 160, 200),
            'scrollbar': pygame.Color(60, 60, 60),
            'scrollbar_handle': pygame.Color(100, 100, 100),
            'line_numbers': pygame.Color(128, 128, 128),
            'error_text': pygame.Color(255, 100, 100),
            'warning_text': pygame.Color(255, 255, 100),
            'info_text': pygame.Color(100, 200, 255),
            'debug_text': pygame.Color(200, 200, 200),
            'system_text': pygame.Color(150, 150, 255),
        }

        # Clear existing colors
        self.themed_colors.clear()

        # Try to get colors from theme - check multiple approaches
        for color_name, default_color in color_mappings.items():
            theme_color = None

            # Try different ways to get the color from theme
            try:
                # Try with console_panel object id
                theme_color = self.ui_manager.ui_theme.get_colour(
                    object_id='#console_panel',
                    colour_id=color_name
                )
            except:
                try:
                    # Try with element type
                    theme_color = self.ui_manager.ui_theme.get_colour(
                        element_type='console_panel',
                        colour_id=color_name
                    )
                except:
                    try:
                        # Try direct lookup in theme data
                        theme_data = self.ui_manager.ui_theme.ui_element_fonts_info
                        if 'console_panel' in theme_data:
                            colours = theme_data['console_panel'].get('colours', {})
                            if color_name in colours:
                                color_str = colours[color_name]
                                if color_str.startswith('#'):
                                    theme_color = pygame.Color(color_str)
                    except:
                        pass

            self.themed_colors[color_name] = theme_color if theme_color else default_color

        # Get themed font
        try:
            self.themed_font = self.ui_manager.ui_theme.get_font(
                object_ids=['#console_panel'],
                element_ids=['console_panel']
            )
        except:
            try:
                self.themed_font = self.ui_manager.ui_theme.get_font(
                    element_types=['console_panel']
                )
            except:
                self.themed_font = None

    def get_color(self, color_name: str) -> pygame.Color:
        """Get themed color with fallback"""
        return self.themed_colors.get(color_name, pygame.Color(255, 255, 255))

    def get_font(self):
        """Get themed font with fallback"""
        if self.themed_font:
            return self.themed_font
        return pygame.font.Font(None, 14)

    def update_theme(self):
        """Update theme data (call when theme changes)"""
        self._update_theme_data()


class ConsoleCommandHandler:
    """Handles command execution and management"""

    def __init__(self, config: ConsoleConfig):
        self.config = config
        self.python_globals = {}
        self.python_locals = {}
        self.command_history: List[str] = []
        self.history_index = -1

        # Initialize Python environment
        if config.behavior.enable_python_exec:
            self._init_python_environment()

    def _init_python_environment(self):
        """Initialize Python execution environment"""
        # Safe globals for Python execution
        safe_globals = {
            '__builtins__': {
                'abs': abs, 'all': all, 'any': any, 'bin': bin, 'bool': bool,
                'chr': chr, 'dict': dict, 'dir': dir, 'divmod': divmod,
                'enumerate': enumerate, 'eval': eval, 'filter': filter,
                'float': float, 'format': format, 'hex': hex, 'int': int,
                'isinstance': isinstance, 'len': len, 'list': list, 'map': map,
                'max': max, 'min': min, 'oct': oct, 'ord': ord, 'pow': pow,
                'print': print, 'range': range, 'repr': repr, 'reversed': reversed,
                'round': round, 'set': set, 'sorted': sorted, 'str': str,
                'sum': sum, 'tuple': tuple, 'type': type, 'zip': zip,
            }
        }

        if not self.config.behavior.sandbox_python_execution:
            # Allow more built-ins in non-sandboxed mode
            safe_globals['__builtins__'] = __builtins__

        self.python_globals = safe_globals
        self.python_locals = {}

    def execute_command(self, command: str) -> Tuple[str, ConsoleOutputType]:
        """Execute a command and return result"""
        if not command.strip():
            return "", ConsoleOutputType.RESULT

        # Add to history
        if self.config.interaction.enable_history:
            self.add_to_history(command)

        # Check for custom commands first
        if self.config.behavior.enable_custom_commands:
            result = self._try_custom_command(command)
            if result is not None:
                return result

        # Check for aliases
        command = self._resolve_alias(command)

        # Execute based on mode
        if self.config.mode == ConsoleMode.PYTHON:
            return self._execute_python(command)
        elif self.config.mode == ConsoleMode.SHELL:
            return self._execute_shell(command)
        else:
            return self._execute_custom(command)

    def _try_custom_command(self, command: str) -> Optional[Tuple[str, ConsoleOutputType]]:
        """Try to execute as custom command"""
        parts = command.split()
        if not parts:
            return None

        command_name = parts[0]
        args = parts[1:]

        # Check built-in commands
        if command_name == "clear":
            return "", ConsoleOutputType.SYSTEM
        elif command_name == "help":
            return self._get_help_text(), ConsoleOutputType.INFO
        elif command_name == "history":
            return self._get_history_text(), ConsoleOutputType.INFO
        elif command_name == "alias":
            return self._handle_alias_command(args), ConsoleOutputType.INFO
        elif command_name == "macro":
            return self._handle_macro_command(args), ConsoleOutputType.INFO

        # Check custom commands
        if command_name in self.config.custom_commands:
            try:
                result = self.config.custom_commands[command_name](args)
                return str(result), ConsoleOutputType.RESULT
            except Exception as e:
                return f"Error in custom command: {e}", ConsoleOutputType.ERROR

        return None

    def _resolve_alias(self, command: str) -> str:
        """Resolve command aliases"""
        parts = command.split()
        if parts and parts[0] in self.config.command_aliases:
            parts[0] = self.config.command_aliases[parts[0]]
            return " ".join(parts)
        return command

    def _execute_python(self, command: str) -> Tuple[str, ConsoleOutputType]:
        """Execute Python code"""
        if not self.config.behavior.enable_python_exec:
            return "Python execution disabled", ConsoleOutputType.ERROR

        try:
            # Capture stdout and stderr
            old_stdout = sys.stdout
            old_stderr = sys.stderr
            captured_output = io.StringIO()
            captured_error = io.StringIO()

            if self.config.behavior.capture_stdout:
                sys.stdout = captured_output
            if self.config.behavior.capture_stderr:
                sys.stderr = captured_error

            try:
                # Try to evaluate as expression first
                result = eval(command, self.python_globals, self.python_locals)
                if result is not None:
                    print(repr(result))
            except SyntaxError:
                # If it's not an expression, execute as statement
                exec(command, self.python_globals, self.python_locals)

            # Restore stdout/stderr
            sys.stdout = old_stdout
            sys.stderr = old_stderr

            # Get captured output
            output = captured_output.getvalue()
            error = captured_error.getvalue()

            if error:
                return error.strip(), ConsoleOutputType.ERROR
            elif output:
                return output.strip(), ConsoleOutputType.RESULT
            else:
                return "", ConsoleOutputType.RESULT

        except Exception as e:
            sys.stdout = old_stdout
            sys.stderr = old_stderr
            return f"{type(e).__name__}: {e}", ConsoleOutputType.ERROR

    def _execute_shell(self, command: str) -> Tuple[str, ConsoleOutputType]:
        """Execute shell command"""
        if not self.config.behavior.enable_shell_commands:
            return "Shell commands disabled", ConsoleOutputType.ERROR

        try:
            import subprocess
            result = subprocess.run(command, shell=True, capture_output=True, text=True)
            if result.returncode == 0:
                return result.stdout.strip(), ConsoleOutputType.RESULT
            else:
                return result.stderr.strip(), ConsoleOutputType.ERROR
        except Exception as e:
            return f"Shell error: {e}", ConsoleOutputType.ERROR

    def _execute_custom(self, command: str) -> Tuple[str, ConsoleOutputType]:
        """Execute custom command"""
        return f"Unknown command: {command}", ConsoleOutputType.ERROR

    def add_to_history(self, command: str):
        """Add command to history"""
        if command and (not self.command_history or self.command_history[-1] != command):
            self.command_history.append(command)
            if len(self.command_history) > self.config.behavior.max_history_size:
                self.command_history.pop(0)
        self.history_index = len(self.command_history)

    def get_history_item(self, direction: int) -> Optional[str]:
        """Get history item (direction: -1 for up, 1 for down)"""
        if not self.command_history:
            return None

        self.history_index += direction
        self.history_index = max(0, min(len(self.command_history), self.history_index))

        if self.history_index >= len(self.command_history):
            return ""

        return self.command_history[self.history_index]

    def get_completions(self, text: str) -> List[str]:
        """Get command completions"""
        if not text:
            return []

        completions = []

        # Python completions
        if self.config.mode == ConsoleMode.PYTHON:
            # Built-in functions
            for name in dir(builtins):
                if name.startswith(text):
                    completions.append(name)

            # Variables in locals/globals
            for name in list(self.python_locals.keys()) + list(self.python_globals.keys()):
                if name.startswith(text):
                    completions.append(name)

        # Custom commands
        for cmd in self.config.custom_commands.keys():
            if cmd.startswith(text):
                completions.append(cmd)

        # Aliases
        for alias in self.config.command_aliases.keys():
            if alias.startswith(text):
                completions.append(alias)

        return sorted(list(set(completions)))

    def _get_help_text(self) -> str:
        """Get help text"""
        help_lines = [
            "Console Commands:",
            "  clear - Clear console output",
            "  help - Show this help",
            "  history - Show command history",
            "  alias [name] [command] - Create command alias",
            "  macro [name] [commands...] - Create command macro",
        ]

        if self.config.custom_commands:
            help_lines.append("\nCustom Commands:")
            for cmd in sorted(self.config.custom_commands.keys()):
                help_lines.append(f"  {cmd}")

        return "\n".join(help_lines)

    def _get_history_text(self) -> str:
        """Get history text"""
        if not self.command_history:
            return "No command history"

        lines = ["Command History:"]
        for i, cmd in enumerate(self.command_history[-10:], 1):  # Show last 10
            lines.append(f"  {i}: {cmd}")

        return "\n".join(lines)

    def _handle_alias_command(self, args: List[str]) -> Tuple[str, ConsoleOutputType]:
        """Handle alias command"""
        if len(args) == 0:
            # List aliases
            if not self.config.command_aliases:
                return "No aliases defined"

            lines = ["Aliases:"]
            for alias, command in self.config.command_aliases.items():
                lines.append(f"  {alias} -> {command}")
            return "\n".join(lines)

        elif len(args) >= 2:
            # Create alias
            alias_name = args[0]
            alias_command = " ".join(args[1:])
            self.config.command_aliases[alias_name] = alias_command
            return f"Created alias: {alias_name} -> {alias_command}"

        else:
            return "Usage: alias [name] [command]"

    def _handle_macro_command(self, args: List[str]) -> Tuple[str, ConsoleOutputType]:
        """Handle macro command"""
        if len(args) == 0:
            # List macros
            if not self.config.macros:
                return "No macros defined"

            lines = ["Macros:"]
            for name, commands in self.config.macros.items():
                lines.append(f"  {name}: {len(commands)} commands")
            return "\n".join(lines)

        elif len(args) >= 2:
            # Create macro
            macro_name = args[0]
            macro_commands = args[1:]  # Each arg is a command
            self.config.macros[macro_name] = macro_commands
            return f"Created macro: {macro_name} with {len(macro_commands)} commands"

        else:
            return "Usage: macro [name] [command1] [command2] ..."


class ConsolePanel(UIElement):
    """Main console/terminal panel widget with comprehensive configuration"""

    def __init__(self, relative_rect: pygame.Rect,
                 manager: pygame_gui.UIManager,
                 config: ConsoleConfig = None,
                 container: IContainerLikeInterface = None,
                 object_id: Union[ObjectID, str, None] = None,
                 anchors: Dict[str, str] = None):

        # Handle object_id properly
        if isinstance(object_id, ObjectID):
            self._object_id = object_id
        elif isinstance(object_id, str):
            self._object_id = ObjectID(object_id=object_id, class_id=None)
        else:
            self._object_id = ObjectID(object_id='#console_panel', class_id=None)

        super().__init__(relative_rect, manager, container,
                         starting_height=1, layer_thickness=1,
                         anchors=anchors, object_id=self._object_id)

        self.config = config or ConsoleConfig()

        # Create theme manager
        element_ids = ['console_panel']
        if hasattr(self, 'object_ids') and self.object_ids:
            element_ids.extend(self.object_ids)
        self.theme_manager = ConsoleThemeManager(manager, element_ids)

        # Create command handler
        self.command_handler = ConsoleCommandHandler(self.config)

        # Create syntax highlighter
        self.syntax_highlighter = ConsoleSyntaxHighlighter(self.config.syntax_theme)

        # Console state
        self.output_buffer: List[ConsoleOutputEntry] = []
        self.current_input = ""
        self.input_cursor_pos = 0
        self.input_selection_start = -1
        self.input_selection_end = -1

        # Display state
        self.scroll_y = 0
        self.max_scroll_y = 0
        self.visible_lines = 0
        self.is_focused = False

        # Held keys
        self.held_keys: Set[int] = set()
        self.key_repeat_timers: Dict[int, float] = {}
        self.key_repeat_initial_delay = self.config.interaction.key_repeat_initial_delay
        self.key_repeat_rate = self.config.interaction.key_repeat_rate

        # Input state
        self.cursor_visible = True
        self.last_cursor_blink = 0
        self.multiline_input = False
        self.completion_candidates: List[str] = []
        self.completion_index = -1

        # Layout rectangles
        self.output_rect = pygame.Rect(0, 0, 0, 0)
        self.input_rect = pygame.Rect(0, 0, 0, 0)
        self.scrollbar_rect = pygame.Rect(0, 0, 0, 0)

        # Filtering
        self.output_filter = ""
        self.filtered_output: List[ConsoleOutputEntry] = []

        # Initialize
        self._calculate_layout()
        self._update_theme_data()

        # Create the image surface
        self.image = pygame.Surface(self.rect.size).convert()

        # Add welcome message
        if self.config.behavior.show_welcome_message:
            self._add_welcome_message()

        # Initial render
        self.rebuild_image()

    def _force_theme_update(self, theme_dict: dict):
        """Force update theme colors from dictionary"""
        if 'console_panel' in theme_dict and 'colours' in theme_dict['console_panel']:
            colors = theme_dict['console_panel']['colours']
            for color_name, color_value in colors.items():
                if color_value.startswith('#'):
                    self.theme_manager.themed_colors[color_name] = pygame.Color(color_value)
            self.rebuild_image()

    def _calculate_layout(self):
        """Calculate layout rectangles"""
        padding = self.config.layout.panel_padding
        input_height = self.config.layout.input_height
        scrollbar_width = self.config.layout.scrollbar_width

        # Input area at bottom
        self.input_rect = pygame.Rect(
            padding,
            self.rect.height - input_height - padding,
            self.rect.width - 2 * padding - scrollbar_width,
            input_height
        )

        # Output area above input
        self.output_rect = pygame.Rect(
            padding,
            padding,
            self.rect.width - 2 * padding - scrollbar_width,
            self.rect.height - input_height - 3 * padding
        )

        # Scrollbar on right
        self.scrollbar_rect = pygame.Rect(
            self.rect.width - scrollbar_width - padding,
            padding,
            scrollbar_width,
            self.rect.height - 2 * padding
        )

        # Calculate visible lines
        line_height = self.config.layout.output_line_height
        self.visible_lines = max(1, self.output_rect.height // line_height)

    def _update_theme_data(self):
        """Update theme-dependent data"""
        self.theme_manager.update_theme()

    def _add_welcome_message(self):
        """Add welcome message to output"""
        welcome_text = f"Console {self.config.mode.value.title()} Mode - Type 'help' for commands"
        self._add_output(welcome_text, ConsoleOutputType.SYSTEM)

    def _add_output(self, text: str, output_type: ConsoleOutputType = ConsoleOutputType.RESULT):
        """Add text to output buffer"""
        if not text:
            return

        # Split multi-line text
        lines = text.split('\n')
        for line in lines:
            entry = ConsoleOutputEntry(
                text=line,
                output_type=output_type,
                timestamp=time.time(),
                line_number=len(self.output_buffer) + 1
            )
            self.output_buffer.append(entry)

        # Limit buffer size
        max_lines = self.config.layout.max_output_lines
        if len(self.output_buffer) > max_lines:
            self.output_buffer = self.output_buffer[-max_lines:]

        # Update filtered output
        self._update_filtered_output()

        # Auto-scroll if enabled
        if self.config.behavior.auto_scroll_output:
            self._scroll_to_bottom()

        # Update display
        self.rebuild_image()

        # Send event
        event_data = {
            'text': text,
            'output_type': output_type,
            'ui_element': self,
            'ui_object_id': self.most_specific_combined_id
        }
        pygame.event.post(pygame.event.Event(UI_CONSOLE_OUTPUT_ADDED, event_data))

    def _update_filtered_output(self):
        """Update filtered output based on current filter"""
        if not self.output_filter:
            self.filtered_output = self.output_buffer[:]
        else:
            case_sensitive = self.config.behavior.filter_case_sensitive
            filter_text = self.output_filter if case_sensitive else self.output_filter.lower()

            self.filtered_output = []
            for entry in self.output_buffer:
                search_text = entry.text if case_sensitive else entry.text.lower()
                if filter_text in search_text:
                    self.filtered_output.append(entry)

        # Update scroll limits
        self._update_scroll_limits()

    def _update_scroll_limits(self):
        """Update scrolling limits"""
        total_lines = len(self.filtered_output)
        self.max_scroll_y = max(0, total_lines - self.visible_lines)
        self.scroll_y = min(self.scroll_y, self.max_scroll_y)

    def _scroll_to_bottom(self):
        """Scroll to bottom of output"""
        self.scroll_y = self.max_scroll_y

    def rebuild_image(self):
        """Rebuild the console image"""
        # Fill background
        bg_color = self.theme_manager.get_color('console_bg')
        self.image.fill(bg_color)

        # Draw output area
        self._draw_output()

        # Draw input area
        self._draw_input()

        # Draw scrollbar
        self._draw_scrollbar()

        # Draw borders
        self._draw_borders()

    def _draw_output(self):
        """Draw the output area"""
        if self.output_rect.width <= 0 or self.output_rect.height <= 0:
            return

        try:
            output_surface = self.image.subsurface(self.output_rect)
        except (ValueError, pygame.error):
            return

        # Background
        bg_color = self.theme_manager.get_color('output_bg')
        output_surface.fill(bg_color)

        # Get font
        font = self.theme_manager.get_font()
        line_height = self.config.layout.output_line_height

        # Draw visible lines
        start_line = self.scroll_y
        end_line = min(start_line + self.visible_lines, len(self.filtered_output))

        for i in range(start_line, end_line):
            entry = self.filtered_output[i]
            y_pos = (i - start_line) * line_height

            # Get color for this output type
            color = self._get_output_color(entry.output_type)

            # Format text with optional timestamps and line numbers
            display_text = self._format_output_text(entry)

            # Render text with word wrapping if enabled
            if self.config.behavior.word_wrap:
                self._draw_wrapped_text(output_surface, display_text, color,
                                        self.config.layout.output_padding, y_pos,
                                        self.output_rect.width - 2 * self.config.layout.output_padding,
                                        font, line_height)
            else:
                try:
                    if hasattr(font, 'render_premul'):
                        text_surface = font.render_premul(display_text, color)
                    else:
                        text_surface = font.render(display_text, True, color)

                    output_surface.blit(text_surface, (self.config.layout.output_padding, y_pos))
                except:
                    pass

    def _get_output_color(self, output_type: ConsoleOutputType) -> pygame.Color:
        """Get color for output type"""
        color_map = {
            ConsoleOutputType.COMMAND: self.theme_manager.get_color('text'),
            ConsoleOutputType.RESULT: self.theme_manager.get_color('text'),
            ConsoleOutputType.ERROR: self.theme_manager.get_color('error_text'),
            ConsoleOutputType.WARNING: self.theme_manager.get_color('warning_text'),
            ConsoleOutputType.INFO: self.theme_manager.get_color('info_text'),
            ConsoleOutputType.DEBUG: self.theme_manager.get_color('debug_text'),
            ConsoleOutputType.SYSTEM: self.theme_manager.get_color('system_text'),
        }
        return color_map.get(output_type, self.theme_manager.get_color('text'))

    def _format_output_text(self, entry: ConsoleOutputEntry) -> str:
        """Format output text with optional prefixes"""
        text = entry.text

        if self.config.behavior.show_line_numbers:
            text = f"{entry.line_number:4d}: {text}"

        if self.config.behavior.show_timestamps:
            timestamp = time.strftime("%H:%M:%S", time.localtime(entry.timestamp))
            text = f"[{timestamp}] {text}"

        return text

    def _draw_wrapped_text(self, surface: pygame.Surface, text: str, color: pygame.Color,
                           x: int, y: int, max_width: int, font, line_height: int):
        """Draw text with word wrapping"""
        if not text:
            return

        words = text.split(' ')
        lines = []
        current_line = ""

        for word in words:
            test_line = current_line + (" " if current_line else "") + word
            try:
                if hasattr(font, 'size'):
                    text_width = font.size(test_line)[0]
                else:
                    text_width = len(test_line) * 8  # Fallback

                if text_width <= max_width:
                    current_line = test_line
                else:
                    if current_line:
                        lines.append(current_line)
                        current_line = word
                    else:
                        lines.append(word)  # Word too long, add anyway
            except:
                current_line = test_line

        if current_line:
            lines.append(current_line)

        # Draw lines
        for i, line in enumerate(lines):
            line_y = y + i * line_height
            if line_y + line_height > surface.get_height():
                break

            try:
                if hasattr(font, 'render_premul'):
                    text_surface = font.render_premul(line, color)
                else:
                    text_surface = font.render(line, True, color)

                surface.blit(text_surface, (x, line_y))
            except:
                pass

    def _draw_input(self):
        """Draw the input area"""
        if self.input_rect.width <= 0 or self.input_rect.height <= 0:
            return

        try:
            input_surface = self.image.subsurface(self.input_rect)
        except (ValueError, pygame.error):
            return

        # Background
        bg_color = self.theme_manager.get_color('input_bg')
        input_surface.fill(bg_color)

        # Draw prompt and input text
        font = self.theme_manager.get_font()
        padding = self.config.layout.input_padding

        # Prompt
        prompt_text = self.config.continuation_prompt if self.multiline_input else self.config.prompt_text
        if self.config.behavior.show_command_prompt:
            prompt_color = self.theme_manager.get_color('prompt')
            try:
                if hasattr(font, 'render_premul'):
                    prompt_surface = font.render_premul(prompt_text, prompt_color)
                else:
                    prompt_surface = font.render(prompt_text, True, prompt_color)

                input_surface.blit(prompt_surface, (padding, padding))
                prompt_width = prompt_surface.get_width()
            except:
                prompt_width = len(prompt_text) * 8  # Fallback
        else:
            prompt_width = 0

        # Input text with syntax highlighting if enabled
        text_x = padding + prompt_width + self.config.layout.prompt_spacing
        text_y = padding

        if self.config.interaction.enable_syntax_highlighting and self.current_input:
            self._draw_highlighted_input(input_surface, text_x, text_y, font)
        else:
            # Draw plain input text
            text_color = self.theme_manager.get_color('text')
            try:
                if hasattr(font, 'render_premul'):
                    text_surface = font.render_premul(self.current_input, text_color)
                else:
                    text_surface = font.render(self.current_input, True, text_color)

                input_surface.blit(text_surface, (text_x, text_y))
            except:
                pass

        # Draw cursor
        if self.is_focused and self.cursor_visible:
            self._draw_cursor(input_surface, text_x, text_y, font)

        # Draw selection
        if self.input_selection_start >= 0 and self.input_selection_end >= 0:
            self._draw_selection(input_surface, text_x, text_y, font)

    def _draw_highlighted_input(self, surface: pygame.Surface, x: int, y: int, font):
        """Draw input text with syntax highlighting"""
        if not self.current_input:
            return

        tokens = self.syntax_highlighter.highlight(self.current_input)
        current_x = x

        for text_chunk, token_type in tokens:
            if not text_chunk:
                continue

            color = self.syntax_highlighter.colors.get(token_type,
                                                       self.theme_manager.get_color('text'))

            try:
                if hasattr(font, 'render_premul'):
                    chunk_surface = font.render_premul(text_chunk, color)
                else:
                    chunk_surface = font.render(text_chunk, True, color)

                surface.blit(chunk_surface, (current_x, y))
                current_x += chunk_surface.get_width()
            except:
                current_x += len(text_chunk) * 8  # Fallback

    def _draw_cursor(self, surface: pygame.Surface, text_x: int, text_y: int, font):
        """Draw input cursor"""
        if self.input_cursor_pos > len(self.current_input):
            self.input_cursor_pos = len(self.current_input)

        # Calculate cursor position
        cursor_text = self.current_input[:self.input_cursor_pos]
        try:
            if hasattr(font, 'size'):
                cursor_x = text_x + font.size(cursor_text)[0]
                cursor_height = font.size("A")[1]
            else:
                cursor_x = text_x + len(cursor_text) * 8  # Fallback
                cursor_height = 16
        except:
            cursor_x = text_x + len(cursor_text) * 8
            cursor_height = 16

        # Draw cursor line
        cursor_color = self.theme_manager.get_color('cursor')
        cursor_width = self.config.layout.cursor_width
        cursor_rect = pygame.Rect(cursor_x, text_y, cursor_width, cursor_height)
        pygame.draw.rect(surface, cursor_color, cursor_rect)

    def _draw_selection(self, surface: pygame.Surface, text_x: int, text_y: int, font):
        """Draw text selection"""
        if self.input_selection_start == self.input_selection_end:
            return

        start = min(self.input_selection_start, self.input_selection_end)
        end = max(self.input_selection_start, self.input_selection_end)

        # Calculate selection bounds
        start_text = self.current_input[:start]
        selected_text = self.current_input[start:end]

        try:
            if hasattr(font, 'size'):
                start_x = text_x + font.size(start_text)[0]
                selected_width = font.size(selected_text)[0]
                selection_height = font.size("A")[1]
            else:
                start_x = text_x + len(start_text) * 8
                selected_width = len(selected_text) * 8
                selection_height = 16
        except:
            start_x = text_x + len(start_text) * 8
            selected_width = len(selected_text) * 8
            selection_height = 16

        # Draw selection background
        selection_color = self.theme_manager.get_color('selection')
        selection_color.a = self.config.layout.selection_alpha
        selection_rect = pygame.Rect(start_x, text_y, selected_width, selection_height)

        # Create temporary surface for alpha blending
        temp_surface = pygame.Surface((selected_width, selection_height))
        temp_surface.fill(selection_color)
        temp_surface.set_alpha(self.config.layout.selection_alpha)
        surface.blit(temp_surface, (start_x, text_y))

    def _draw_scrollbar(self):
        """Draw scrollbar"""
        if self.scrollbar_rect.width <= 0 or self.scrollbar_rect.height <= 0:
            return

        try:
            scrollbar_surface = self.image.subsurface(self.scrollbar_rect)
        except (ValueError, pygame.error):
            return

        # Background
        bg_color = self.theme_manager.get_color('scrollbar')
        scrollbar_surface.fill(bg_color)

        # Handle
        if self.max_scroll_y > 0:
            handle_height = max(20, (self.visible_lines * self.scrollbar_rect.height) //
                                len(self.filtered_output))
            handle_y = (self.scroll_y * (self.scrollbar_rect.height - handle_height)) // self.max_scroll_y

            handle_rect = pygame.Rect(2, handle_y, self.scrollbar_rect.width - 4, handle_height)
            handle_color = self.theme_manager.get_color('scrollbar_handle')
            pygame.draw.rect(scrollbar_surface, handle_color, handle_rect)

    def _draw_borders(self):
        """Draw panel borders"""
        border_color = self.theme_manager.get_color('border')
        border_width = self.config.layout.border_width

        # Main border
        pygame.draw.rect(self.image, border_color, self.image.get_rect(), border_width)

        # Focus border
        if self.is_focused:
            focus_color = self.theme_manager.get_color('focus_border')
            focus_width = self.config.layout.focus_border_width
            pygame.draw.rect(self.image, focus_color, self.image.get_rect(), focus_width)

        # Separator between output and input
        separator_y = self.input_rect.y - self.config.layout.panel_padding // 2
        pygame.draw.line(self.image, border_color,
                         (self.config.layout.panel_padding, separator_y),
                         (self.rect.width - self.config.layout.panel_padding, separator_y),
                         border_width)

    def _start_key_repeat(self, key: int):
        """Start key repeat for a specific key"""
        self.held_keys.add(key)
        self.key_repeat_timers[key] = time.time() + self.key_repeat_initial_delay

    def _stop_key_repeat(self, key: int):
        """Stop key repeat for a specific key"""
        self.held_keys.discard(key)
        if key in self.key_repeat_timers:
            del self.key_repeat_timers[key]

    def _process_key_repeats(self):
        """Process held keys for repeating"""
        current_time = time.time()
        keys_to_repeat = []

        for key in self.held_keys.copy():
            if key in self.key_repeat_timers:
                if current_time >= self.key_repeat_timers[key]:
                    keys_to_repeat.append(key)
                    # Set next repeat time
                    self.key_repeat_timers[key] = current_time + self.key_repeat_rate

        # Execute repeated key actions
        for key in keys_to_repeat:
            self._execute_key_repeat(key)

    def _execute_key_repeat(self, key: int):
        """Execute the action for a repeated key"""
        if key == pygame.K_BACKSPACE:
            self._handle_backspace()
        elif key == pygame.K_DELETE:
            self._handle_delete()
        elif key == pygame.K_LEFT:
            self._move_cursor(-1, False)
        elif key == pygame.K_RIGHT:
            self._move_cursor(1, False)

    def process_event(self, event: pygame.event.Event) -> bool:
        """Process events for the console"""
        consumed = False

        if event.type == pygame.KEYDOWN and self.is_focused:
            consumed = self._handle_key_down(event)

        elif event.type == pygame.KEYUP and self.is_focused:
            consumed = self._handle_key_up(event)

        elif event.type == pygame.MOUSEBUTTONDOWN:
            consumed = self._handle_mouse_down(event)

        elif event.type == pygame.MOUSEBUTTONUP:
            consumed = self._handle_mouse_up(event)

        elif event.type == pygame.MOUSEMOTION:
            consumed = self._handle_mouse_motion(event)

        elif event.type == pygame.MOUSEWHEEL:
            consumed = self._handle_mouse_wheel(event)

        # Don't handle TEXTINPUT events - we handle text in keydown
        elif event.type == pygame.TEXTINPUT:
            consumed = False

        return consumed

    def _handle_key_down(self, event: pygame.event.Event) -> bool:
        """Handle key down events"""
        key = event.key
        mods = event.mod

        # Check for shortcuts with modifiers
        if mods & pygame.KMOD_CTRL:
            if key == self.config.interaction.clear_shortcut:  # Ctrl+L
                self.clear_output()
                return True
            elif key == self.config.interaction.interrupt_key:  # Ctrl+C
                self._interrupt_current_command()
                return True
            elif key == pygame.K_a:  # Ctrl+A - Select all
                self._select_all_input()
                return True
            elif key == pygame.K_c:  # Ctrl+C - Copy (if no interrupt)
                if not (mods & pygame.KMOD_SHIFT):
                    self._copy_selection()
                    return True
            elif key == pygame.K_v:  # Ctrl+V - Paste
                self._paste_text()
                return True

        # Handle regular keys
        if key == self.config.interaction.execute_key:  # Enter
            if mods & pygame.KMOD_SHIFT:
                if self.config.interaction.multiline_key == pygame.K_RETURN:
                    self._add_newline()
                    return True
            else:
                self._execute_current_input()
                return True

        elif key == self.config.interaction.history_up:  # Up arrow
            self._navigate_history(-1)
            return True

        elif key == self.config.interaction.history_down:  # Down arrow
            self._navigate_history(1)
            return True

        elif key == self.config.interaction.autocomplete_key:  # Tab
            self._handle_autocomplete()
            return True

        elif key == pygame.K_BACKSPACE:
            self._handle_backspace()
            self._start_key_repeat(key)  # Start repeat for backspace
            return True

        elif key == pygame.K_DELETE:
            self._handle_delete()
            self._start_key_repeat(key)  # Start repeat for delete
            return True

        elif key == pygame.K_LEFT:
            self._move_cursor(-1, mods & pygame.KMOD_SHIFT)
            if not (mods & pygame.KMOD_SHIFT):  # Only repeat if not selecting
                self._start_key_repeat(key)
            return True

        elif key == pygame.K_RIGHT:
            self._move_cursor(1, mods & pygame.KMOD_SHIFT)
            if not (mods & pygame.KMOD_SHIFT):  # Only repeat if not selecting
                self._start_key_repeat(key)
            return True

        elif key == pygame.K_HOME:
            self._move_cursor_to_start(mods & pygame.KMOD_SHIFT)
            return True

        elif key == pygame.K_END:
            self._move_cursor_to_end(mods & pygame.KMOD_SHIFT)
            return True

        # Handle text input - only for printable characters that aren't special keys
        elif (event.unicode and event.unicode.isprintable() and
              not (mods & (pygame.KMOD_CTRL | pygame.KMOD_ALT)) and
              key not in [pygame.K_RETURN, pygame.K_TAB, pygame.K_BACKSPACE, pygame.K_DELETE]):
            self._insert_text(event.unicode)
            return True

        return False

    def _handle_key_up(self, event: pygame.event.Event) -> bool:
        """Handle key up events"""
        # Stop key repeat for released keys
        self._stop_key_repeat(event.key)
        return False

    def _handle_mouse_down(self, event: pygame.event.Event) -> bool:
        """Handle mouse down events"""
        mouse_pos = event.pos
        relative_pos = (mouse_pos[0] - self.rect.x, mouse_pos[1] - self.rect.y)

        # Check if click is within panel
        if not (0 <= relative_pos[0] < self.rect.width and
                0 <= relative_pos[1] < self.rect.height):
            # Lost focus - stop all key repeats
            if self.is_focused:
                self.held_keys.clear()
                self.key_repeat_timers.clear()
            self.is_focused = False
            return False

        # Focus the panel
        self.is_focused = True

        # Check different areas
        if self.input_rect.collidepoint(relative_pos):
            # Click in input area - position cursor
            self._position_cursor_from_mouse(relative_pos)
            return True

        elif self.output_rect.collidepoint(relative_pos):
            # Click in output area - start selection
            if self.config.interaction.enable_mouse_selection:
                self._start_output_selection(relative_pos)
            return True

        elif self.scrollbar_rect.collidepoint(relative_pos):
            # Click in scrollbar
            self._handle_scrollbar_click(relative_pos)
            return True

        return True

    def _handle_mouse_up(self, event: pygame.event.Event) -> bool:
        """Handle mouse up events"""
        return False

    def _handle_mouse_motion(self, event: pygame.event.Event) -> bool:
        """Handle mouse motion events"""
        return False

    def _handle_mouse_wheel(self, event: pygame.event.Event) -> bool:
        """Handle mouse wheel events"""
        if hasattr(event, 'y'):
            scroll_amount = -event.y * self.config.layout.scroll_speed
            self._scroll_output(scroll_amount)
            return True
        return False

    def _execute_current_input(self):
        """Execute the current input command"""
        if not self.current_input.strip():
            return

        # Add command to output
        if self.config.behavior.show_command_prompt:
            command_text = f"{self.config.prompt_text}{self.current_input}"
        else:
            command_text = self.current_input

        self._add_output(command_text, ConsoleOutputType.COMMAND)

        # Execute command
        try:
            result, output_type = self.command_handler.execute_command(self.current_input)
            if result:
                self._add_output(result, output_type)
        except Exception as e:
            self._add_output(f"Execution error: {e}", ConsoleOutputType.ERROR)

        # Clear input
        self.current_input = ""
        self.input_cursor_pos = 0
        self.input_selection_start = -1
        self.input_selection_end = -1
        self.multiline_input = False

        # Send event
        event_data = {
            'command': command_text,
            'ui_element': self,
            'ui_object_id': self.most_specific_combined_id
        }
        pygame.event.post(pygame.event.Event(UI_CONSOLE_COMMAND_EXECUTED, event_data))

        self.rebuild_image()

    def _navigate_history(self, direction: int):
        """Navigate command history"""
        if not self.config.interaction.enable_history:
            return

        history_item = self.command_handler.get_history_item(direction)
        if history_item is not None:
            self.current_input = history_item
            self.input_cursor_pos = len(self.current_input)
            self.input_selection_start = -1
            self.input_selection_end = -1
            self.rebuild_image()

    def _handle_autocomplete(self):
        """Handle tab completion"""
        if not self.config.interaction.enable_autocomplete:
            return

        # Get word at cursor
        cursor_pos = self.input_cursor_pos
        text = self.current_input

        # Find word boundaries
        word_start = cursor_pos
        while word_start > 0 and text[word_start - 1].isalnum():
            word_start -= 1

        word_end = cursor_pos
        while word_end < len(text) and text[word_end].isalnum():
            word_end += 1

        current_word = text[word_start:word_end]

        if not current_word:
            return

        # Get completions
        completions = self.command_handler.get_completions(current_word)

        if not completions:
            return

        if len(completions) == 1:
            # Single completion - insert it
            completion = completions[0]
            new_text = text[:word_start] + completion + text[word_end:]
            self.current_input = new_text
            self.input_cursor_pos = word_start + len(completion)
        else:
            # Multiple completions - show them
            self._add_output("Completions: " + ", ".join(completions), ConsoleOutputType.INFO)

        self.rebuild_image()

    def _insert_text(self, text: str):
        """Insert text at cursor position"""
        if self.input_selection_start >= 0 and self.input_selection_end >= 0:
            # Replace selection
            start = min(self.input_selection_start, self.input_selection_end)
            end = max(self.input_selection_start, self.input_selection_end)
            self.current_input = self.current_input[:start] + text + self.current_input[end:]
            self.input_cursor_pos = start + len(text)
            self.input_selection_start = -1
            self.input_selection_end = -1
        else:
            # Insert at cursor
            self.current_input = (self.current_input[:self.input_cursor_pos] + text +
                                  self.current_input[self.input_cursor_pos:])
            self.input_cursor_pos += len(text)

        self.rebuild_image()

    def _handle_backspace(self):
        """Handle backspace key"""
        if self.input_selection_start >= 0 and self.input_selection_end >= 0:
            # Delete selection
            start = min(self.input_selection_start, self.input_selection_end)
            end = max(self.input_selection_start, self.input_selection_end)
            self.current_input = self.current_input[:start] + self.current_input[end:]
            self.input_cursor_pos = start
            self.input_selection_start = -1
            self.input_selection_end = -1
        elif self.input_cursor_pos > 0:
            # Delete character before cursor
            self.current_input = (self.current_input[:self.input_cursor_pos - 1] +
                                  self.current_input[self.input_cursor_pos:])
            self.input_cursor_pos -= 1

        self.rebuild_image()

    def _handle_delete(self):
        """Handle delete key"""
        if self.input_selection_start >= 0 and self.input_selection_end >= 0:
            # Delete selection
            start = min(self.input_selection_start, self.input_selection_end)
            end = max(self.input_selection_start, self.input_selection_end)
            self.current_input = self.current_input[:start] + self.current_input[end:]
            self.input_cursor_pos = start
            self.input_selection_start = -1
            self.input_selection_end = -1
        elif self.input_cursor_pos < len(self.current_input):
            # Delete character after cursor
            self.current_input = (self.current_input[:self.input_cursor_pos] +
                                  self.current_input[self.input_cursor_pos + 1:])

        self.rebuild_image()

    def _move_cursor(self, direction: int, select: bool = False):
        """Move cursor left or right"""
        new_pos = max(0, min(len(self.current_input), self.input_cursor_pos + direction))

        if select:
            if self.input_selection_start < 0:
                self.input_selection_start = self.input_cursor_pos
            self.input_selection_end = new_pos
        else:
            self.input_selection_start = -1
            self.input_selection_end = -1

        self.input_cursor_pos = new_pos
        self.rebuild_image()

    def _move_cursor_to_start(self, select: bool = False):
        """Move cursor to start of input"""
        if select:
            if self.input_selection_start < 0:
                self.input_selection_start = self.input_cursor_pos
            self.input_selection_end = 0
        else:
            self.input_selection_start = -1
            self.input_selection_end = -1

        self.input_cursor_pos = 0
        self.rebuild_image()

    def _move_cursor_to_end(self, select: bool = False):
        """Move cursor to end of input"""
        if select:
            if self.input_selection_start < 0:
                self.input_selection_start = self.input_cursor_pos
            self.input_selection_end = len(self.current_input)
        else:
            self.input_selection_start = -1
            self.input_selection_end = -1

        self.input_cursor_pos = len(self.current_input)
        self.rebuild_image()

    def _select_all_input(self):
        """Select all input text"""
        self.input_selection_start = 0
        self.input_selection_end = len(self.current_input)
        self.rebuild_image()

    def _copy_selection(self):
        """Copy selected text to clipboard"""
        if self.input_selection_start >= 0 and self.input_selection_end >= 0:
            start = min(self.input_selection_start, self.input_selection_end)
            end = max(self.input_selection_start, self.input_selection_end)
            selected_text = self.current_input[start:end]
            # Note: pygame doesn't have built-in clipboard support
            # This would require a third-party library like pyperclip
            print(f"Would copy to clipboard: {selected_text}")

    def _paste_text(self):
        """Paste text from clipboard"""
        # Note: pygame doesn't have built-in clipboard support
        # This would require a third-party library like pyperclip
        # For now, just simulate with a sample text
        paste_text = "# Pasted text"
        self._insert_text(paste_text)

    def _add_newline(self):
        """Add newline to current input (multiline mode)"""
        self.multiline_input = True
        self._insert_text('\n')

    def interrupt_current_command(self):
        """Interrupt current command execution"""
        self._add_output("^C KeyboardInterrupt", ConsoleOutputType.ERROR)
        self.current_input = ""
        self.input_cursor_pos = 0
        self.input_selection_start = -1
        self.input_selection_end = -1
        self.multiline_input = False
        self.rebuild_image()

    def _position_cursor_from_mouse(self, mouse_pos: Tuple[int, int]):
        """Position cursor based on mouse click"""
        # This is a simplified implementation
        # In practice, you'd need to calculate exact character positions
        relative_x = mouse_pos[0] - self.input_rect.x - self.config.layout.input_padding

        # Rough approximation based on average character width
        font = self.theme_manager.get_font()
        try:
            if hasattr(font, 'size'):
                char_width = font.size("W")[0]  # Use wide character for approximation
            else:
                char_width = 8  # Fallback
        except:
            char_width = 8

        # Account for prompt
        if self.config.behavior.show_command_prompt:
            prompt_text = self.config.continuation_prompt if self.multiline_input else self.config.prompt_text
            try:
                if hasattr(font, 'size'):
                    prompt_width = font.size(prompt_text)[0]
                else:
                    prompt_width = len(prompt_text) * char_width
            except:
                prompt_width = len(prompt_text) * char_width

            relative_x -= (prompt_width + self.config.layout.prompt_spacing)

        # Calculate cursor position
        if relative_x <= 0:
            self.input_cursor_pos = 0
        else:
            estimated_pos = relative_x // char_width
            self.input_cursor_pos = min(len(self.current_input), max(0, estimated_pos))

        # Clear selection
        self.input_selection_start = -1
        self.input_selection_end = -1

        self.rebuild_image()

    def _start_output_selection(self, mouse_pos: Tuple[int, int]):
        """Start selecting output text"""
        # This would implement output text selection
        # For now, just focus the panel
        pass

    def _handle_scrollbar_click(self, mouse_pos: Tuple[int, int]):
        """Handle scrollbar click"""
        relative_y = mouse_pos[1] - self.scrollbar_rect.y
        scroll_ratio = relative_y / self.scrollbar_rect.height
        self.scroll_y = int(scroll_ratio * self.max_scroll_y)
        self.rebuild_image()

    def _scroll_output(self, amount: int):
        """Scroll output by specified amount"""
        self.scroll_y = max(0, min(self.max_scroll_y, self.scroll_y + amount))
        self.rebuild_image()

    def update(self, time_delta: float):
        """Update console (handle cursor blinking, key repeats, etc.)"""
        super().update(time_delta)

        # Handle cursor blinking
        current_time = time.time()
        if current_time - self.last_cursor_blink > self.config.interaction.cursor_blink_rate:
            self.cursor_visible = not self.cursor_visible
            self.last_cursor_blink = current_time
            if self.is_focused:
                self.rebuild_image()

        # Process key repeats
        if self.is_focused:
            self._process_key_repeats()

    def clear_output(self):
        """Clear console output"""
        if not self.config.behavior.preserve_output_on_clear:
            self.output_buffer.clear()
            self.filtered_output.clear()
            self.scroll_y = 0
            self.max_scroll_y = 0
            self.rebuild_image()

            # Send event
            event_data = {
                'ui_element': self,
                'ui_object_id': self.most_specific_combined_id
            }
            pygame.event.post(pygame.event.Event(UI_CONSOLE_CLEAR_REQUESTED, event_data))

    def set_output_filter(self, filter_text: str):
        """Set output filter"""
        self.output_filter = filter_text
        self._update_filtered_output()
        self.rebuild_image()

        # Send event
        event_data = {
            'filter_text': filter_text,
            'ui_element': self,
            'ui_object_id': self.most_specific_combined_id
        }
        pygame.event.post(pygame.event.Event(UI_CONSOLE_FILTER_CHANGED, event_data))

    def add_custom_command(self, name: str, handler: Callable):
        """Add custom command handler"""
        self.config.custom_commands[name] = handler

    def add_alias(self, alias: str, command: str):
        """Add command alias"""
        self.config.command_aliases[alias] = command

    def add_macro(self, name: str, commands: List[str]):
        """Add command macro"""
        self.config.macros[name] = commands

    def execute_command(self, command: str):
        """Execute command programmatically"""
        self.current_input = command
        self._execute_current_input()

    def set_theme(self, theme: ConsoleSyntaxTheme):
        """Change syntax highlighting theme"""
        self.config.syntax_theme = theme
        self.syntax_highlighter = ConsoleSyntaxHighlighter(theme)
        self.rebuild_image()

    def rebuild_from_changed_theme_data(self):
        """Rebuild when theme data changes"""
        self._update_theme_data()
        self.rebuild_image()


# Default theme for console panel
CONSOLE_THEME = {
    "console_panel": {
        "colours": {
            "console_bg": "#1a1a1a",
            "input_bg": "#2a2a2a",
            "output_bg": "#1f1f1f",
            "text": "#ffffff",
            "prompt": "#00ff00",
            "cursor": "#ffffff",
            "selection": "#6464ff",
            "border": "#505050",
            "focus_border": "#78a8c8",
            "scrollbar": "#3c3c3c",
            "scrollbar_handle": "#646464",
            "line_numbers": "#808080",
            "error_text": "#ff6464",
            "warning_text": "#ffff64",
            "info_text": "#64c8ff",
            "debug_text": "#c8c8c8",
            "system_text": "#9696ff"
        },
        "font": {
            "name": "courier",
            "size": "12",
            "bold": "0",
            "italic": "0"
        },
        "misc": {
            "border_width": "1"
        }
    }
}


def create_sample_commands() -> Dict[str, Callable]:
    """Create sample custom commands for demonstration"""

    def hello_command(args: List[str]) -> str:
        if args:
            return f"Hello, {' '.join(args)}!"
        return "Hello, World!"

    def math_command(args: List[str]) -> str:
        if len(args) < 3:
            return "Usage: math <number> <operator> <number>"

        try:
            a = float(args[0])
            op = args[1]
            b = float(args[2])

            if op == '+':
                result = a + b
            elif op == '-':
                result = a - b
            elif op == '*':
                result = a * b
            elif op == '/':
                result = a / b if b != 0 else "Division by zero"
            else:
                return f"Unknown operator: {op}"

            return f"{a} {op} {b} = {result}"
        except ValueError:
            return "Invalid numbers"

    def info_command(args: List[str]) -> str:
        import platform
        import sys

        info_lines = [
            f"Python: {sys.version}",
            f"Platform: {platform.platform()}",
            f"Pygame: {pygame.version.ver}",
            f"Console Panel: Ready"
        ]

        return "\n".join(info_lines)

    return {
        'hello': hello_command,
        'math': math_command,
        'info': info_command
    }


def main():
    """Example demonstration of the Console Panel"""
    pygame.init()
    screen = pygame.display.set_mode((1000, 700))
    pygame.display.set_caption("Configurable Console Panel Demo")
    clock = pygame.time.Clock()

    # Create manager with theme
    manager = pygame_gui.UIManager((1000, 700), CONSOLE_THEME)

    # Create different configurations for demonstration

    # Standard configuration
    standard_config = ConsoleConfig()
    standard_config.custom_commands = create_sample_commands()
    standard_config.command_aliases = {
        'll': 'ls -la',
        'q': 'quit',
        'h': 'help'
    }
    standard_config.macros = {
        'setup': ['clear', 'info', 'hello Console'],
        'test': ['math 10 + 5', 'math 20 * 3']
    }

    # Compact configuration
    compact_layout = ConsoleLayoutConfig()
    compact_layout.input_height = 25
    compact_layout.output_line_height = 14
    compact_layout.panel_padding = 4
    compact_layout.fallback_font_size = 10

    compact_config = ConsoleConfig()
    compact_config.layout = compact_layout
    compact_config.behavior.show_timestamps = False
    compact_config.behavior.show_line_numbers = False
    compact_config.behavior.show_welcome_message = False
    compact_config.custom_commands = create_sample_commands()

    # Large configuration with all features
    large_layout = ConsoleLayoutConfig()
    large_layout.input_height = 40
    large_layout.output_line_height = 18
    large_layout.panel_padding = 12
    large_layout.cursor_width = 3
    large_layout.fallback_font_size = 14

    large_behavior = ConsoleBehaviorConfig()
    large_behavior.show_timestamps = True
    large_behavior.show_line_numbers = True
    large_behavior.word_wrap = True
    large_behavior.enable_output_filtering = True

    large_config = ConsoleConfig()
    large_config.layout = large_layout
    large_config.behavior = large_behavior
    large_config.custom_commands = create_sample_commands()
    large_config.syntax_theme = ConsoleSyntaxTheme.DARK

    # Create console with standard config initially
    console = ConsolePanel(
        pygame.Rect(50, 50, 600, 400),
        manager,
        standard_config,
        object_id=ObjectID(object_id='#main_console', class_id='@console_panel')
    )

    # Create a second smaller console for comparison
    mini_console = ConsolePanel(
        pygame.Rect(670, 50, 280, 200),
        manager,
        compact_config,
        object_id=ObjectID(object_id='#mini_console', class_id='@console_panel')
    )

    # Instructions
    print("\nConfigurable Console Panel Demo")
    print("\nControls:")
    print("- Type commands and press Enter")
    print("- Use Up/Down arrows for history")
    print("- Tab for auto-completion")
    print("- Ctrl+L to clear")
    print("- Ctrl+C to interrupt")
    print("\nBuilt-in commands: help, clear, history, alias, macro, hello, math, info")
    print("Python expressions: 2+2, len('hello'), [x**2 for x in range(5)]")
    print("\nPress number keys for different configurations:")
    print("1 - Standard config  2 - Compact config  3 - Large config")
    print("T - Toggle light/dark theme  F - Toggle output filter")

    # Demo variables
    current_config = "standard"
    light_theme = False
    filter_active = False

    running = True
    while running:
        time_delta = clock.tick(60) / 1000.0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            # Handle custom console events first
            elif event.type == UI_CONSOLE_COMMAND_EXECUTED:
                if CONSOLE_DEBUG:
                    print(f"Command executed: {event.command}")

            elif event.type == UI_CONSOLE_OUTPUT_ADDED:
                if CONSOLE_DEBUG:
                    print(f"Output added: {event.text[:50]}...")

            # Process console events first
            console_consumed = console.process_event(event)
            mini_console_consumed = mini_console.process_event(event)

            # Only process hotkeys if no console consumed the event AND no console is focused
            should_process_hotkeys = (not (console_consumed or mini_console_consumed) and
                                      not (console.is_focused or mini_console.is_focused))

            # Handle demo hotkeys only when not typing in console
            if event.type == pygame.KEYDOWN and should_process_hotkeys:
                if event.key == pygame.K_1:
                    # Switch to standard configuration
                    console.config = standard_config
                    console._calculate_layout()
                    console._update_theme_data()
                    console.rebuild_image()
                    current_config = "standard"
                    print("Switched to: Standard Configuration")

                elif event.key == pygame.K_2:
                    # Switch to compact configuration
                    console.config = compact_config
                    console._calculate_layout()
                    console._update_theme_data()
                    console.rebuild_image()
                    current_config = "compact"
                    print("Switched to: Compact Configuration")

                elif event.key == pygame.K_3:
                    # Switch to large configuration
                    console.config = large_config
                    console._calculate_layout()
                    console._update_theme_data()
                    console.rebuild_image()
                    current_config = "large"
                    print("Switched to: Large Configuration")

                elif event.key == pygame.K_t:
                    # Toggle theme
                    light_theme = not light_theme
                    if light_theme:
                        # Light theme
                        new_theme = {
                            "console_panel": {
                                "colours": {
                                    "console_bg": "#f8f8f8",
                                    "input_bg": "#ffffff",
                                    "output_bg": "#fafafa",
                                    "text": "#000000",
                                    "prompt": "#0080ff",
                                    "cursor": "#000000",
                                    "selection": "#a0a0ff",
                                    "border": "#c0c0c0",
                                    "focus_border": "#4080ff",
                                    "scrollbar": "#e0e0e0",
                                    "scrollbar_handle": "#a0a0a0",
                                    "line_numbers": "#808080",
                                    "error_text": "#c00000",
                                    "warning_text": "#c08000",
                                    "info_text": "#0080c0",
                                    "debug_text": "#606060",
                                    "system_text": "#8000c0"
                                },
                                "font": {
                                    "name": "courier",
                                    "size": "12",
                                    "bold": "0",
                                    "italic": "0"
                                }
                            }
                        }
                        manager.get_theme().load_theme(new_theme)
                        console._force_theme_update(new_theme)
                        mini_console._force_theme_update(new_theme)
                        console.set_theme(ConsoleSyntaxTheme.LIGHT)
                        mini_console.set_theme(ConsoleSyntaxTheme.LIGHT)
                    else:
                        # Dark theme
                        manager.get_theme().load_theme(CONSOLE_THEME)
                        console._force_theme_update(CONSOLE_THEME)
                        mini_console._force_theme_update(CONSOLE_THEME)
                        console.set_theme(ConsoleSyntaxTheme.DARK)
                        mini_console.set_theme(ConsoleSyntaxTheme.DARK)

                    print(f"Switched to: {'Light' if light_theme else 'Dark'} Theme")

                elif event.key == pygame.K_f:
                    # Toggle output filter
                    filter_active = not filter_active
                    if filter_active:
                        console.set_output_filter("info")
                        print("Filter activated: showing only 'info' lines")
                    else:
                        console.set_output_filter("")
                        print("Filter cleared: showing all output")

            # Let the manager handle other events only if consoles didn't consume them
            if not (console_consumed or mini_console_consumed):
                manager.process_events(event)

        # Update
        manager.update(time_delta)
        console.update(time_delta)
        mini_console.update(time_delta)

        # Draw
        screen.fill((40, 40, 40))

        # Draw demo info
        font = pygame.font.Font(None, 24)
        info_text = font.render("Console Panel Demo", True, pygame.Color(255, 255, 255))
        screen.blit(info_text, (50, 20))

        # Show current state
        y_offset = 470
        info_font = pygame.font.Font(None, 16)

        # Configuration info
        config_info = [
            f"Configuration: {current_config.title()}",
            f"Theme: {'Light' if light_theme else 'Dark'}",
            f"Input Height: {console.config.layout.input_height}px",
            f"Line Height: {console.config.layout.output_line_height}px",
            f"Show Timestamps: {'Yes' if console.config.behavior.show_timestamps else 'No'}",
            f"Show Line Numbers: {'Yes' if console.config.behavior.show_line_numbers else 'No'}",
            f"Syntax Highlighting: {'Yes' if console.config.interaction.enable_syntax_highlighting else 'No'}",
            f"Filter Active: {'Yes' if filter_active else 'No'}"
        ]

        for i, info in enumerate(config_info):
            color = pygame.Color(200, 200, 200)
            text = info_font.render(info, True, color)
            screen.blit(text, (50, y_offset + i * 18))

        # Console stats
        y_offset = 470
        console_stats = [
            f"Output Lines: {len(console.output_buffer)}",
            f"Filtered Lines: {len(console.filtered_output)}",
            f"History Items: {len(console.command_handler.command_history)}",
            f"Custom Commands: {len(console.config.custom_commands)}",
            f"Aliases: {len(console.config.command_aliases)}",
            f"Macros: {len(console.config.macros)}",
            f"Scroll Position: {console.scroll_y}/{console.max_scroll_y}",
            f"Focused: {'Main' if console.is_focused else 'Mini' if mini_console.is_focused else 'None'}"
        ]

        for i, stat in enumerate(console_stats):
            color = pygame.Color(180, 180, 180)
            text = info_font.render(stat, True, color)
            screen.blit(text, (670, y_offset + i * 18))

        manager.draw_ui(screen)
        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()