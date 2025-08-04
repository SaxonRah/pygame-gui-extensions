import pygame
import pygame_gui
from pygame_gui.core import UIElement, ObjectID
from pygame_gui.core.interfaces import IContainerLikeInterface
from typing import List, Optional, Dict, Any, Union, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
import json
import time
import hashlib
from pathlib import Path
import threading
from queue import Queue

try:
    from pygame_gui.core.interfaces.gui_font_interface import IGUIFontInterface
except ImportError:
    IGUIFontInterface = None

# Optional PIL support for better thumbnail generation
try:
    from PIL import Image as PILImage

    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

ASSET_DEBUG = False

# Define custom pygame-gui events
UI_ASSET_SELECTED = pygame.USEREVENT + 100
UI_ASSET_DOUBLE_CLICKED = pygame.USEREVENT + 101
UI_ASSET_RIGHT_CLICKED = pygame.USEREVENT + 102
UI_ASSET_DRAG_STARTED = pygame.USEREVENT + 103
UI_ASSET_DROP_COMPLETED = pygame.USEREVENT + 104
UI_ASSET_IMPORT_REQUESTED = pygame.USEREVENT + 105
UI_ASSET_EXPORT_REQUESTED = pygame.USEREVENT + 106
UI_ASSET_METADATA_CHANGED = pygame.USEREVENT + 107
UI_ASSET_COLLECTION_CHANGED = pygame.USEREVENT + 108
UI_ASSET_SEARCH_UPDATED = pygame.USEREVENT + 109


class AssetType(Enum):
    """Supported asset types"""
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    MODEL = "model"
    TEXT = "text"
    SCRIPT = "script"
    FONT = "font"
    MATERIAL = "material"
    ANIMATION = "animation"
    PREFAB = "prefab"
    SCENE = "scene"
    OTHER = "other"

    def __lt__(self, other):
        """Enable sorting of AssetType enums"""
        if isinstance(other, AssetType):
            return self.value < other.value
        return NotImplemented


class AssetViewMode(Enum):
    """Asset browser view modes"""
    GRID = "grid"
    LIST = "list"
    DETAIL = "detail"


class AssetSortMode(Enum):
    """Asset sorting options"""
    NAME = "name"
    TYPE = "type"
    SIZE = "size"
    DATE_MODIFIED = "date_modified"
    DATE_CREATED = "date_created"


@dataclass
class AssetLayoutConfig:
    """Layout and spacing configuration for asset browser"""
    # Grid layout settings
    grid_item_width: int = 160
    grid_item_height: int = 180
    grid_padding: int = 8
    grid_columns: int = 0  # Auto-calculate if 0
    grid_thumbnail_size: Tuple[int, int] = (128, 128)

    # List layout settings
    list_item_height: int = 32
    list_thumbnail_size: int = 28
    list_text_padding: int = 8

    # Detail layout settings
    detail_item_height: int = 80
    detail_thumbnail_size: int = 64
    detail_text_padding: int = 8
    detail_metadata_spacing: int = 2

    # Common layout settings
    item_padding: int = 4
    text_padding: int = 2
    border_width: int = 1
    focus_border_width: int = 2
    selection_border_width: int = 2

    # Thumbnail settings
    thumbnail_border_width: int = 1
    thumbnail_corner_radius: int = 2

    # Loading indicator settings
    loading_indicator_size: int = 16
    loading_indicator_thickness: int = 2

    # Grid line settings
    grid_line_width: int = 1
    show_grid_lines: bool = False


@dataclass
class AssetInteractionConfig:
    """Interaction and timing configuration"""
    # Click and selection
    double_click_time: int = 500  # milliseconds
    drag_threshold: int = 5  # pixels
    selection_click_tolerance: int = 2  # pixels

    # Scrolling
    scroll_speed: int = 3
    scroll_margin: int = 10
    smooth_scroll: bool = False

    # Performance settings
    max_visible_items: int = 1000
    lazy_loading_threshold: int = 500
    thumbnail_generation_delay: float = 0.1

    # Cache settings
    thumbnail_cache_size: int = 200
    metadata_cache_size: int = 1000

    # Animation timing
    loading_animation_speed: float = 2.0  # rotations per second
    hover_transition_time: float = 0.1  # seconds


@dataclass
class AssetBehaviorConfig:
    """Behavior configuration for asset browser"""
    # Selection behavior
    allow_multi_select: bool = True
    allow_empty_selection: bool = True
    select_on_hover: bool = False
    focus_follows_mouse: bool = True

    # Interaction behavior
    allow_drag_drop: bool = True
    allow_reordering: bool = False
    double_click_action: str = "open"  # "open", "edit", "select"
    right_click_action: str = "context_menu"  # "context_menu", "select"

    # Display behavior
    show_file_extensions: bool = True
    show_metadata_overlay: bool = True
    show_loading_indicators: bool = True
    show_tooltips: bool = True
    truncate_long_names: bool = True

    # Search and filtering behavior
    search_in_metadata: bool = True
    search_in_tags: bool = True
    search_in_filename: bool = True
    case_sensitive_search: bool = False
    filter_by_type: bool = True
    real_time_search: bool = True

    # Thumbnail behavior
    auto_generate_thumbnails: bool = True
    cache_thumbnails: bool = True
    lazy_loading: bool = True
    preload_adjacent_thumbnails: bool = True

    # Performance behavior
    enable_background_loading: bool = True
    limit_simultaneous_loads: int = 3
    unload_distant_thumbnails: bool = True

    # Visual behavior
    animate_loading: bool = True
    highlight_search_matches: bool = True
    fade_disabled_items: bool = True


@dataclass
class AssetConfig:
    """Complete configuration for the asset browser"""
    # Sub-configurations
    layout: AssetLayoutConfig = field(default_factory=AssetLayoutConfig)
    interaction: AssetInteractionConfig = field(default_factory=AssetInteractionConfig)
    behavior: AssetBehaviorConfig = field(default_factory=AssetBehaviorConfig)

    # Default view settings
    default_view_mode: AssetViewMode = AssetViewMode.GRID
    sort_mode: AssetSortMode = AssetSortMode.NAME
    sort_ascending: bool = True

    # Convenience properties for backward compatibility
    @property
    def thumbnail_size(self) -> Tuple[int, int]:
        return self.layout.grid_thumbnail_size

    @property
    def grid_columns(self) -> int:
        return self.layout.grid_columns

    @property
    def allow_multi_select(self) -> bool:
        return self.behavior.allow_multi_select

    @property
    def allow_drag_drop(self) -> bool:
        return self.behavior.allow_drag_drop

    @property
    def double_click_time(self) -> int:
        return self.interaction.double_click_time

    @property
    def max_visible_items(self) -> int:
        return self.interaction.max_visible_items


@dataclass
class AssetMetadata:
    """Metadata for an asset"""
    # File information
    file_size: int = 0
    date_created: float = 0.0
    date_modified: float = 0.0
    file_hash: Optional[str] = None

    # Asset-specific data
    width: Optional[int] = None
    height: Optional[int] = None
    duration: Optional[float] = None
    format: Optional[str] = None
    color_depth: Optional[int] = None
    compression: Optional[str] = None

    # User-defined metadata
    title: Optional[str] = None
    description: Optional[str] = None
    author: Optional[str] = None
    copyright: Optional[str] = None
    tags: Set[str] = field(default_factory=set)
    rating: int = 0  # 0-5 stars
    favorite: bool = False

    # Custom properties
    custom_data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert metadata to dictionary for serialization"""
        return {
            'file_size': self.file_size,
            'date_created': self.date_created,
            'date_modified': self.date_modified,
            'file_hash': self.file_hash,
            'width': self.width,
            'height': self.height,
            'duration': self.duration,
            'format': self.format,
            'color_depth': self.color_depth,
            'compression': self.compression,
            'title': self.title,
            'description': self.description,
            'author': self.author,
            'copyright': self.copyright,
            'tags': list(self.tags),
            'rating': self.rating,
            'favorite': self.favorite,
            'custom_data': self.custom_data
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AssetMetadata':
        """Create metadata from dictionary"""
        metadata = cls()
        for key, value in data.items():
            if key == 'tags':
                metadata.tags = set(value) if value else set()
            elif hasattr(metadata, key):
                setattr(metadata, key, value)
        return metadata


@dataclass
class AssetItem:
    """Represents a single asset"""
    id: str
    name: str
    file_path: Path
    asset_type: AssetType
    metadata: AssetMetadata = field(default_factory=AssetMetadata)
    thumbnail_path: Optional[Path] = None
    collection_id: Optional[str] = None

    # Runtime data
    thumbnail_surface: Optional[pygame.Surface] = None
    is_loading_thumbnail: bool = False
    last_access_time: float = field(default_factory=time.time)

    def get_file_extension(self) -> str:
        """Get file extension"""
        return self.file_path.suffix.lower()

    def get_display_name(self, config: AssetConfig) -> str:
        """Get display name with configuration support"""
        display_name = self.metadata.title or self.name

        # Add file extension if configured
        if config.behavior.show_file_extensions and not self.metadata.title:
            display_name += self.get_file_extension()

        # Truncate if configured and too long
        if config.behavior.truncate_long_names:
            max_chars = 30 if config.default_view_mode == AssetViewMode.GRID else 50
            if len(display_name) > max_chars:
                display_name = display_name[:max_chars - 3] + "..."

        return display_name

    def get_file_size_str(self) -> str:
        """Get human-readable file size"""
        size = self.metadata.file_size
        if size < 1024:
            return f"{size} B"
        elif size < 1024 * 1024:
            return f"{size / 1024:.1f} KB"
        elif size < 1024 * 1024 * 1024:
            return f"{size / (1024 * 1024):.1f} MB"
        else:
            return f"{size / (1024 * 1024 * 1024):.1f} GB"

    def matches_search(self, query: str, config: AssetConfig) -> bool:
        """Check if asset matches search query with configuration support"""
        if not query:
            return True

        if not config.behavior.case_sensitive_search:
            query = query.lower()

        def check_text(text: str) -> bool:
            if not text:
                return False
            if not config.behavior.case_sensitive_search:
                text = text.lower()
            return query in text

        # Check filename if configured
        if config.behavior.search_in_filename and check_text(self.name):
            return True

        # Check title
        if check_text(self.metadata.title):
            return True

        # Check metadata if configured
        if config.behavior.search_in_metadata:
            if check_text(self.metadata.description):
                return True
            if check_text(self.metadata.author):
                return True

        # Check tags if configured
        if config.behavior.search_in_tags:
            for tag in self.metadata.tags:
                if check_text(tag):
                    return True

        # Check file extension
        if check_text(self.get_file_extension()):
            return True

        return False

    def has_tag(self, tag: str) -> bool:
        """Check if asset has a specific tag"""
        return tag.lower() in [t.lower() for t in self.metadata.tags]


@dataclass
class AssetCollection:
    """Represents a collection/folder of assets"""
    id: str
    name: str
    description: str = ""
    asset_ids: Set[str] = field(default_factory=set)
    parent_id: Optional[str] = None
    children_ids: Set[str] = field(default_factory=set)
    color: Optional[pygame.Color] = None
    icon_name: Optional[str] = None
    expanded: bool = True
    order: int = 0

    # Metadata
    created_time: float = field(default_factory=time.time)
    modified_time: float = field(default_factory=time.time)

    def add_asset(self, asset_id: str):
        """Add asset to collection"""
        self.asset_ids.add(asset_id)
        self.modified_time = time.time()

    def remove_asset(self, asset_id: str):
        """Remove asset from collection"""
        self.asset_ids.discard(asset_id)
        self.modified_time = time.time()


class AssetThemeManager:
    """Manages theming for the asset browser panel"""

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
            'dark_bg': pygame.Color(40, 40, 40),
            'normal_text': pygame.Color(255, 255, 255),
            'secondary_text': pygame.Color(180, 180, 180),
            'disabled_text': pygame.Color(120, 120, 120),
            'selected_bg': pygame.Color(70, 130, 180),
            'hovered_bg': pygame.Color(60, 60, 60),
            'focused_bg': pygame.Color(100, 160, 220),
            'normal_border': pygame.Color(100, 100, 100),
            'focus_border': pygame.Color(255, 255, 255),
            'selection_border': pygame.Color(120, 160, 255),
            'thumbnail_border': pygame.Color(80, 80, 80),
            'grid_line': pygame.Color(60, 60, 60),
            'loading_indicator': pygame.Color(100, 200, 100),
            'accent': pygame.Color(100, 200, 100),
            'error': pygame.Color(200, 100, 100),
            'warning': pygame.Color(200, 200, 100),
            'success': pygame.Color(100, 200, 100),
            'placeholder_bg': pygame.Color(50, 50, 50),
            'metadata_bg': pygame.Color(30, 30, 30, 128),
        }

        try:
            self.themed_colors = {}
            theme = self.ui_manager.get_theme()

            for color_id, default_color in color_mappings.items():
                try:
                    if hasattr(theme, 'get_colour_or_gradient'):
                        color = theme.get_colour_or_gradient(color_id, self.element_ids)
                        self.themed_colors[color_id] = color if color else default_color
                    else:
                        self.themed_colors[color_id] = default_color
                except Exception:
                    self.themed_colors[color_id] = default_color

            # Get themed font
            try:
                if hasattr(theme, 'get_font'):
                    self.themed_font = theme.get_font(self.element_ids)
                else:
                    raise Exception("No font method")
            except Exception:
                try:
                    self.themed_font = pygame.font.SysFont('Arial', 11)
                except:
                    self.themed_font = pygame.font.Font(None, 11)

        except Exception as e:
            if ASSET_DEBUG:
                print(f"Error getting theme data: {e}")
            # Complete fallback
            self.themed_colors = color_mappings
            try:
                self.themed_font = pygame.font.SysFont('Arial', 11)
            except:
                self.themed_font = pygame.font.Font(None, 11)

    def rebuild_from_changed_theme_data(self):
        """Called when theme data changes"""
        self._update_theme_data()

    def get_color(self, color_id: str, fallback: pygame.Color = None) -> pygame.Color:
        """Get a themed color with fallback"""
        return self.themed_colors.get(color_id, fallback or pygame.Color(255, 255, 255))

    def get_font(self):
        """Get the themed font"""
        return self.themed_font


class AssetPreviewGenerator:
    """Generates thumbnails and previews for assets with improved configuration support"""

    def __init__(self, config: AssetConfig, cache_dir: Path = None):
        self.config = config
        self.cache_dir = cache_dir or Path("asset_cache")
        self.cache_dir.mkdir(exist_ok=True)

        # Background thumbnail generation
        self.generation_queue = Queue()
        self.generation_thread = None
        self.stop_generation = False

        # Supported formats
        self.image_formats = {'.png', '.jpg', '.jpeg', '.bmp', '.tga', '.gif', '.webp'}
        self.text_formats = {'.txt', '.py', '.json', '.xml', '.html', '.css', '.js', '.md'}

        # Cache management
        self.thumbnail_cache = {}
        self.cache_access_times = {}

        if self.config.behavior.enable_background_loading:
            self._start_generation_thread()

    def _start_generation_thread(self):
        """Start background thumbnail generation thread"""
        if self.generation_thread is None or not self.generation_thread.is_alive():
            self.stop_generation = False
            self.generation_thread = threading.Thread(target=self._generation_worker, daemon=True)
            self.generation_thread.start()

    def _generation_worker(self):
        """Background worker for thumbnail generation"""
        while not self.stop_generation:
            try:
                asset_item = self.generation_queue.get(timeout=1.0)
                if asset_item is None:  # Shutdown signal
                    break

                self._generate_thumbnail_sync(asset_item)
                asset_item.is_loading_thumbnail = False

            except:
                continue

    def stop(self):
        """Stop background generation"""
        self.stop_generation = True
        if self.generation_queue:
            self.generation_queue.put(None)  # Signal shutdown
        if self.generation_thread and self.generation_thread.is_alive():
            self.generation_thread.join(timeout=1.0)

    def get_cache_path(self, asset_item: AssetItem, size: Tuple[int, int] = None) -> Path:
        """Get cache file path for asset thumbnail"""
        if size is None:
            size = self.config.thumbnail_size

        # Use file hash for cache key if available
        cache_key = asset_item.metadata.file_hash or asset_item.id
        return self.cache_dir / f"{cache_key}_{size[0]}x{size[1]}.png"

    def has_cached_thumbnail(self, asset_item: AssetItem, size: Tuple[int, int] = None) -> bool:
        """Check if cached thumbnail exists and is up to date"""
        if not self.config.behavior.cache_thumbnails:
            return False

        cache_path = self.get_cache_path(asset_item, size)
        if not cache_path.exists():
            return False

        # Check if cache is newer than source file
        try:
            cache_time = cache_path.stat().st_mtime
            source_time = asset_item.file_path.stat().st_mtime
            return cache_time >= source_time
        except OSError:
            return False

    def get_thumbnail_async(self, asset_item: AssetItem, size: Tuple[int, int] = None) -> pygame.Surface:
        """Get thumbnail asynchronously with configuration support"""
        if size is None:
            size = self.config.thumbnail_size

        cache_key = f"{asset_item.id}_{size[0]}x{size[1]}"

        # Return cached surface if available
        if cache_key in self.thumbnail_cache:
            self.cache_access_times[cache_key] = time.time()
            return self.thumbnail_cache[cache_key]

        # Check for cached file
        if self.config.behavior.cache_thumbnails and self.has_cached_thumbnail(asset_item, size):
            try:
                surface = pygame.image.load(str(self.get_cache_path(asset_item, size)))
                self._cache_surface(cache_key, surface)
                return surface
            except pygame.error:
                pass

        # Queue for background generation if enabled and not already loading
        if (self.config.behavior.auto_generate_thumbnails and
                self.config.behavior.enable_background_loading and
                not asset_item.is_loading_thumbnail):

            asset_item.is_loading_thumbnail = True
            if self.generation_queue:
                self.generation_queue.put(asset_item)

        # Return placeholder
        placeholder = self._create_placeholder_thumbnail(asset_item, size)
        if not asset_item.is_loading_thumbnail and self.config.behavior.auto_generate_thumbnails:
            # Generate synchronously for immediate display
            self._generate_thumbnail_sync(asset_item, size)

        return placeholder

    def _cache_surface(self, cache_key: str, surface: pygame.Surface):
        """Cache a surface with size management"""
        self.thumbnail_cache[cache_key] = surface
        self.cache_access_times[cache_key] = time.time()

        # Manage cache size
        if len(self.thumbnail_cache) > self.config.interaction.thumbnail_cache_size:
            # Remove oldest entries
            oldest_keys = sorted(self.cache_access_times.keys(),
                                 key=lambda k: self.cache_access_times[k])
            for key in oldest_keys[:len(oldest_keys) // 4]:  # Remove 25%
                del self.thumbnail_cache[key]
                del self.cache_access_times[key]

    def _generate_thumbnail_sync(self, asset_item: AssetItem, size: Tuple[int, int] = None):
        """Generate thumbnail synchronously with configuration support"""
        if size is None:
            size = self.config.thumbnail_size

        try:
            surface = None

            if asset_item.asset_type == AssetType.IMAGE:
                surface = self._generate_image_thumbnail(asset_item, size)
            elif asset_item.asset_type == AssetType.TEXT:
                surface = self._generate_text_thumbnail(asset_item, size)
            else:
                surface = self._create_placeholder_thumbnail(asset_item, size)

            # Ensure we always have a valid surface
            if not surface:
                surface = self._create_placeholder_thumbnail(asset_item, size)

            if surface:
                # Save to cache if configured
                if self.config.behavior.cache_thumbnails:
                    try:
                        cache_path = self.get_cache_path(asset_item, size)
                        cache_path.parent.mkdir(parents=True, exist_ok=True)  # Ensure cache dir exists
                        pygame.image.save(surface, str(cache_path))
                    except Exception as cache_error:
                        if ASSET_DEBUG:
                            print(f"Cache save failed for {asset_item.name}: {cache_error}")

                # Store in memory cache
                cache_key = f"{asset_item.id}_{size[0]}x{size[1]}"
                self._cache_surface(cache_key, surface)

                # Store in asset
                asset_item.thumbnail_surface = surface

        except Exception as e:
            if ASSET_DEBUG:
                print(f"Error generating thumbnail for {asset_item.name}: {e}")
            # Create fallback placeholder
            try:
                fallback_surface = self._create_placeholder_thumbnail(asset_item, size)
                cache_key = f"{asset_item.id}_{size[0]}x{size[1]}"
                self._cache_surface(cache_key, fallback_surface)
                asset_item.thumbnail_surface = fallback_surface
            except Exception as fallback_error:
                if ASSET_DEBUG:
                    print(f"Fallback thumbnail creation failed: {fallback_error}")

    def _generate_image_thumbnail(self, asset_item: AssetItem, size: Tuple[int, int]) -> pygame.Surface:
        """Generate thumbnail for image asset"""
        try:
            if PIL_AVAILABLE:
                # Use PIL for better quality
                with PILImage.open(asset_item.file_path) as pil_img:
                    # Convert to RGB if necessary
                    if pil_img.mode not in ('RGB', 'RGBA'):
                        pil_img = pil_img.convert('RGB')

                    # Create thumbnail
                    pil_img.thumbnail(size, PILImage.Resampling.LANCZOS)

                    # Convert to pygame surface
                    mode = pil_img.mode
                    img_size = pil_img.size
                    data = pil_img.tobytes()

                    surface = pygame.image.frombytes(data, img_size, mode)
                    return surface
            else:
                # Use pygame directly
                original = pygame.image.load(str(asset_item.file_path))
                return pygame.transform.scale(original, size)

        except Exception as e:
            if ASSET_DEBUG:
                print(f"Error generating image thumbnail: {e}")
            return self._create_placeholder_thumbnail(asset_item, size)

    def _generate_text_thumbnail(self, asset_item: AssetItem, size: Tuple[int, int]) -> pygame.Surface:
        """Generate thumbnail for text asset"""
        # Try to read file, but fallback to placeholder if it fails
        try:
            if not asset_item.file_path.exists():
                return self._create_placeholder_thumbnail(asset_item, size)

            surface = pygame.Surface(size)
            surface.fill((50, 50, 50))

            # Read first few lines of text
            with open(asset_item.file_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = [line.strip() for line in f.readlines()[:10] if line.strip()]

            if not lines:  # Empty file or no readable lines
                return self._create_placeholder_thumbnail(asset_item, size)

            # Render text
            font_size = max(8, min(12, size[1] // 12))
            font = pygame.font.Font(None, font_size)
            y_offset = 5

            for line in lines[:8]:  # Max 8 lines
                if y_offset > size[1] - 15:
                    break

                # Truncate long lines
                max_chars = size[0] // (font_size // 2)
                if len(line) > max_chars:
                    line = line[:max_chars - 3] + "..."

                text_surface = font.render(line, True, (200, 200, 200))
                surface.blit(text_surface, (5, y_offset))
                y_offset += font_size + 2

            # Draw border
            pygame.draw.rect(surface, (100, 100, 100), surface.get_rect(), 1)
            return surface

        except Exception as e:
            if ASSET_DEBUG:
                print(f"Error generating text thumbnail for {asset_item.name}: {e}")
            # Always fallback to placeholder on any error
            return self._create_placeholder_thumbnail(asset_item, size)

    def _create_placeholder_thumbnail(self, asset_item: AssetItem, size: Tuple[int, int]) -> pygame.Surface:
        """Create placeholder thumbnail based on asset type with configuration support"""
        surface = pygame.Surface(size)

        # Color by type
        type_colors = {
            AssetType.IMAGE: (100, 150, 100),
            AssetType.AUDIO: (150, 100, 150),
            AssetType.VIDEO: (150, 150, 100),
            AssetType.MODEL: (100, 100, 150),
            AssetType.TEXT: (120, 120, 120),
            AssetType.SCRIPT: (150, 120, 100),
            AssetType.FONT: (100, 120, 150),
            AssetType.OTHER: (100, 100, 100),
        }

        color = type_colors.get(asset_item.asset_type, (100, 100, 100))
        surface.fill(color)

        # Draw icon/text
        font_size = max(12, min(24, size[1] // 6))
        font = pygame.font.Font(None, font_size)

        # Type-specific icons (simplified)
        icon_text = {
            AssetType.IMAGE: "IMG",
            AssetType.AUDIO: "SND",
            AssetType.VIDEO: "VID",
            AssetType.MODEL: "3D",
            AssetType.TEXT: "TXT",
            AssetType.SCRIPT: "SCR",
            AssetType.FONT: "FNT",
            AssetType.OTHER: "?",
        }

        text = icon_text.get(asset_item.asset_type, "?")
        text_surface = font.render(text, True, (255, 255, 255))
        text_rect = text_surface.get_rect(center=surface.get_rect().center)
        surface.blit(text_surface, text_rect)

        # Draw border
        border_width = max(1, self.config.layout.thumbnail_border_width)
        pygame.draw.rect(surface, (150, 150, 150), surface.get_rect(), border_width)

        return surface


class AssetItemUI:
    """UI representation of an asset item with comprehensive configuration support"""

    def __init__(self, asset_item: AssetItem, rect: pygame.Rect, config: AssetConfig):
        self.asset_item = asset_item
        self.rect = rect
        self.config = config

        # UI state
        self.is_selected = False
        self.is_hovered = False
        self.is_focused = False
        self.is_dragging = False
        self.hover_alpha = 0.0

        # Layout
        self.thumbnail_rect = pygame.Rect(0, 0, 0, 0)
        self.text_rect = pygame.Rect(0, 0, 0, 0)
        self.metadata_rect = pygame.Rect(0, 0, 0, 0)

        self.calculate_layout()

    def calculate_layout(self):
        """Calculate internal layout based on view mode and configuration"""
        layout = self.config.layout

        if self.config.default_view_mode == AssetViewMode.GRID:
            # Grid layout: thumbnail on top, text below
            padding = layout.grid_padding
            thumb_size = min(self.rect.width - padding * 2,
                             self.rect.height - 30 - padding * 2)

            self.thumbnail_rect = pygame.Rect(
                self.rect.centerx - thumb_size // 2,
                self.rect.y + padding,
                thumb_size,
                thumb_size
            )

            self.text_rect = pygame.Rect(
                self.rect.x + padding,
                self.thumbnail_rect.bottom + layout.text_padding,
                self.rect.width - padding * 2,
                20
            )

        elif self.config.default_view_mode == AssetViewMode.LIST:
            # List layout: small thumbnail on left, text on right
            thumb_size = min(layout.list_thumbnail_size, self.rect.height - 4)

            self.thumbnail_rect = pygame.Rect(
                self.rect.x + layout.item_padding,
                self.rect.y + (self.rect.height - thumb_size) // 2,
                thumb_size,
                thumb_size
            )

            self.text_rect = pygame.Rect(
                self.thumbnail_rect.right + layout.list_text_padding,
                self.rect.y,
                self.rect.width - self.thumbnail_rect.width - layout.list_text_padding - layout.item_padding * 2,
                self.rect.height
            )

        else:  # DETAIL
            # Detail layout: medium thumbnail, text, and metadata
            thumb_size = layout.detail_thumbnail_size

            self.thumbnail_rect = pygame.Rect(
                self.rect.x + layout.item_padding,
                self.rect.y + layout.item_padding,
                thumb_size,
                thumb_size
            )

            self.text_rect = pygame.Rect(
                self.thumbnail_rect.right + layout.detail_text_padding,
                self.rect.y + layout.item_padding,
                self.rect.width - thumb_size - layout.detail_text_padding - layout.item_padding * 2,
                20
            )

            self.metadata_rect = pygame.Rect(
                self.thumbnail_rect.right + layout.detail_text_padding,
                self.text_rect.bottom + layout.detail_metadata_spacing,
                self.rect.width - thumb_size - layout.detail_text_padding - layout.item_padding * 2,
                self.rect.height - 30 - layout.item_padding
            )

    def draw(self, surface: pygame.Surface, theme_manager: AssetThemeManager,
             preview_generator: AssetPreviewGenerator):
        """Draw the asset item with improved theming and configuration support"""
        layout = self.config.layout

        # Background
        if self.is_selected:
            bg_color = theme_manager.get_color('selected_bg')
            pygame.draw.rect(surface, bg_color, self.rect)
        elif self.is_hovered:
            bg_color = theme_manager.get_color('hovered_bg')
            pygame.draw.rect(surface, bg_color, self.rect)

        # Focus border
        if self.is_focused:
            border_color = theme_manager.get_color('focus_border')
            pygame.draw.rect(surface, border_color, self.rect, layout.focus_border_width)

        # Selection border
        if self.is_selected:
            border_color = theme_manager.get_color('selection_border')
            pygame.draw.rect(surface, border_color, self.rect, layout.selection_border_width)

        # Draw thumbnail
        self._draw_thumbnail(surface, theme_manager, preview_generator)

        # Draw text
        self._draw_text(surface, theme_manager)

        # Draw metadata if in detail view
        if (self.config.default_view_mode == AssetViewMode.DETAIL and
                self.config.behavior.show_metadata_overlay):
            self._draw_metadata(surface, theme_manager)

        # Draw loading indicator
        if (self.asset_item.is_loading_thumbnail and
                self.config.behavior.show_loading_indicators):
            self._draw_loading_indicator(surface, theme_manager)

    def _draw_thumbnail(self, surface: pygame.Surface, theme_manager: AssetThemeManager,
                        preview_generator: AssetPreviewGenerator):
        """Draw the asset thumbnail with improved configuration support"""
        # Get thumbnail size based on view mode
        if self.config.default_view_mode == AssetViewMode.GRID:
            thumb_size = self.config.layout.grid_thumbnail_size
        elif self.config.default_view_mode == AssetViewMode.LIST:
            thumb_size = (self.config.layout.list_thumbnail_size, self.config.layout.list_thumbnail_size)
        else:  # DETAIL
            thumb_size = (self.config.layout.detail_thumbnail_size, self.config.layout.detail_thumbnail_size)

        thumbnail = preview_generator.get_thumbnail_async(self.asset_item, thumb_size)

        if thumbnail:
            # Scale thumbnail to fit rect while maintaining aspect ratio
            thumb_rect = thumbnail.get_rect()

            # Calculate scaling to fit within thumbnail_rect
            scale_x = self.thumbnail_rect.width / thumb_rect.width
            scale_y = self.thumbnail_rect.height / thumb_rect.height
            scale = min(scale_x, scale_y)

            new_size = (int(thumb_rect.width * scale), int(thumb_rect.height * scale))

            if new_size != thumb_rect.size:
                scaled_thumbnail = pygame.transform.scale(thumbnail, new_size)
            else:
                scaled_thumbnail = thumbnail

            # Center in thumbnail rect
            pos = (
                self.thumbnail_rect.centerx - new_size[0] // 2,
                self.thumbnail_rect.centery - new_size[1] // 2
            )

            surface.blit(scaled_thumbnail, pos)

        # Draw thumbnail border
        border_color = theme_manager.get_color('thumbnail_border')
        border_width = self.config.layout.thumbnail_border_width
        if border_width > 0:
            pygame.draw.rect(surface, border_color, self.thumbnail_rect, border_width)

    def _draw_text(self, surface: pygame.Surface, theme_manager: AssetThemeManager):
        """Draw asset name text with configuration support"""
        text_color = theme_manager.get_color('normal_text')

        # Get display name with configuration
        display_name = self.asset_item.get_display_name(self.config)

        try:
            font = theme_manager.get_font()
            if hasattr(font, 'render_premul'):
                text_surface = font.render_premul(display_name, text_color)
            else:
                text_surface = font.render(display_name, True, text_color)

            # Position text based on view mode
            if self.config.default_view_mode == AssetViewMode.GRID:
                # Center text in grid mode
                text_pos = (
                    self.text_rect.centerx - text_surface.get_width() // 2,
                    self.text_rect.y
                )
            else:
                # Left-align in list and detail modes
                text_pos = (
                    self.text_rect.x,
                    self.text_rect.centery - text_surface.get_height() // 2
                )

            # Clip text to rect
            clip_rect = self.text_rect.clip(surface.get_rect())
            if clip_rect.width > 0 and clip_rect.height > 0:
                surface.set_clip(clip_rect)
                surface.blit(text_surface, text_pos)
                surface.set_clip(None)

        except Exception as e:
            if ASSET_DEBUG:
                print(f"Error rendering asset text: {e}")

    def _draw_metadata(self, surface: pygame.Surface, theme_manager: AssetThemeManager):
        """Draw metadata in detail view with configuration support"""
        if not self.metadata_rect.width or not self.metadata_rect.height:
            return

        metadata_color = theme_manager.get_color('secondary_text')
        layout = self.config.layout

        # Prepare metadata lines
        lines = []

        # File size
        lines.append(f"Size: {self.asset_item.get_file_size_str()}")

        # Dimensions for images
        if self.asset_item.metadata.width and self.asset_item.metadata.height:
            lines.append(f"Dimensions: {self.asset_item.metadata.width}x{self.asset_item.metadata.height}")

        # Tags
        if self.asset_item.metadata.tags:
            tags_str = ", ".join(list(self.asset_item.metadata.tags)[:3])
            if len(self.asset_item.metadata.tags) > 3:
                tags_str += "..."
            lines.append(f"Tags: {tags_str}")

        # Rating
        if self.asset_item.metadata.rating > 0:
            stars = "*" * self.asset_item.metadata.rating + "_" * (5 - self.asset_item.metadata.rating)
            lines.append(f"Rating: {stars}")

        # Draw lines
        try:
            font = theme_manager.get_font()
            y_offset = self.metadata_rect.y
            line_height = 14

            for line in lines[:3]:  # Max 3 lines
                if y_offset > self.metadata_rect.bottom - line_height:
                    break

                if hasattr(font, 'render_premul'):
                    line_surface = font.render_premul(line, metadata_color)
                else:
                    line_surface = font.render(line, True, metadata_color)

                # Clip to metadata rect
                clip_rect = self.metadata_rect.clip(surface.get_rect())
                if clip_rect.width > 0 and clip_rect.height > 0:
                    surface.set_clip(clip_rect)
                    surface.blit(line_surface, (self.metadata_rect.x, y_offset))
                    surface.set_clip(None)

                y_offset += line_height + layout.detail_metadata_spacing

        except Exception as e:
            if ASSET_DEBUG:
                print(f"Error rendering metadata: {e}")

    def _draw_loading_indicator(self, surface: pygame.Surface, theme_manager: AssetThemeManager):
        """Draw loading indicator with configuration support"""
        if not self.config.behavior.animate_loading:
            return

        layout = self.config.layout
        center = self.thumbnail_rect.center
        radius = layout.loading_indicator_size // 2
        thickness = layout.loading_indicator_thickness

        # Animate based on time
        angle = (time.time() * self.config.interaction.loading_animation_speed * 360) % 360

        # Draw spinning arc
        loading_color = theme_manager.get_color('loading_indicator')

        # Simple pulsing circle since pygame doesn't have easy arc drawing
        alpha = int(127 + 127 * abs(pygame.math.Vector2().rotate(angle).x))
        loading_color_with_alpha = pygame.Color(loading_color.r, loading_color.g, loading_color.b, alpha)

        # Draw outer circle
        pygame.draw.circle(surface, loading_color_with_alpha, center, radius, thickness)

    def contains_point(self, pos: Tuple[int, int]) -> bool:
        """Check if point is within this item"""
        return self.rect.collidepoint(pos)

    def update_selection(self, selected: bool):
        """Update selection state"""
        self.is_selected = selected

    def update_hover(self, hovered: bool):
        """Update hover state"""
        self.is_hovered = hovered

    def update_focus(self, focused: bool):
        """Update focus state"""
        self.is_focused = focused


class AssetBrowserPanel(UIElement):
    """Main asset browser panel widget with comprehensive configuration support"""

    def __init__(self, relative_rect: pygame.Rect,
                 manager: pygame_gui.UIManager,
                 config: AssetConfig = None,
                 container: IContainerLikeInterface = None,
                 object_id: Union[ObjectID, str, None] = None,
                 anchors: Dict[str, str] = None):

        # Handle object_id properly
        if isinstance(object_id, ObjectID):
            self._object_id = object_id
        elif isinstance(object_id, str):
            self._object_id = ObjectID(object_id=object_id, class_id=None)
        else:
            self._object_id = ObjectID(object_id='#asset_browser', class_id=None)

        super().__init__(relative_rect, manager, container,
                         starting_height=1, layer_thickness=1,
                         anchors=anchors, object_id=self._object_id)

        self.config = config or AssetConfig()

        # Create theme manager
        element_ids = ['asset_browser']
        if hasattr(self, 'object_ids') and self.object_ids:
            element_ids.extend(self.object_ids)
        self.theme_manager = AssetThemeManager(manager, element_ids)

        # Asset data
        self.assets: Dict[str, AssetItem] = {}
        self.collections: Dict[str, AssetCollection] = {}
        self.preview_generator = AssetPreviewGenerator(self.config)

        # UI state
        self.asset_item_uis: List[AssetItemUI] = []
        self.visible_assets: List[str] = []
        self.selected_assets: Set[str] = set()
        self.focused_asset: Optional[str] = None
        self.hovered_asset: Optional[str] = None
        self.selection_anchor: Optional[str] = None

        # Current view settings
        self.current_collection: Optional[str] = None
        self.search_query: str = ""
        self.filter_types: Set[AssetType] = set()
        self.view_mode = self.config.default_view_mode

        # Drag and drop state
        self.dragging_assets: Set[str] = set()
        self.drag_start_pos: Optional[Tuple[int, int]] = None
        self.drop_target: Optional[str] = None

        # Scrolling
        self.scroll_y = 0
        self.max_scroll = 0
        self.content_height = 0

        # Performance tracking
        self.last_click_time = 0
        self._force_rebuild = True  # Force initial rebuild

        # Create the image surface
        self.image = pygame.Surface(self.rect.size).convert()

        # Initialize - Force initial build
        self.rebuild_ui()
        self._rebuild_image()

    def __del__(self):
        """Cleanup when destroyed"""
        if hasattr(self, 'preview_generator'):
            self.preview_generator.stop()

    def rebuild_from_changed_theme_data(self):
        """Called when theme data changes"""
        self.theme_manager.rebuild_from_changed_theme_data()
        self._force_rebuild = True
        self.rebuild_ui()
        self._rebuild_image()

    def _filter_and_sort_assets(self) -> List[str]:
        """Filter and sort assets based on current criteria with configuration support"""
        filtered_assets = []

        for asset_id, asset in self.assets.items():
            # Collection filter
            if self.current_collection:
                if asset.collection_id != self.current_collection:
                    continue

            # Type filter
            if self.filter_types and asset.asset_type not in self.filter_types:
                continue

            # Search filter with configuration support
            if self.search_query and not asset.matches_search(self.search_query, self.config):
                continue

            filtered_assets.append(asset_id)

        # Sort assets
        if self.config.sort_mode == AssetSortMode.NAME:
            filtered_assets.sort(
                key=lambda aid: self.assets[aid].get_display_name(self.config).lower(),
                reverse=not self.config.sort_ascending
            )
        elif self.config.sort_mode == AssetSortMode.TYPE:
            filtered_assets.sort(
                key=lambda aid: self.assets[aid].asset_type.value,
                reverse=not self.config.sort_ascending
            )
        elif self.config.sort_mode == AssetSortMode.SIZE:
            filtered_assets.sort(
                key=lambda aid: self.assets[aid].metadata.file_size,
                reverse=not self.config.sort_ascending
            )
        elif self.config.sort_mode == AssetSortMode.DATE_MODIFIED:
            filtered_assets.sort(
                key=lambda aid: self.assets[aid].metadata.date_modified,
                reverse=not self.config.sort_ascending
            )

        return filtered_assets

    def rebuild_ui(self):
        """Rebuild the UI layout with improved performance"""
        # Always rebuild if forced or if assets changed
        if self._force_rebuild or not hasattr(self, 'visible_assets'):
            self._force_rebuild = False
        else:
            return  # Skip if not forced and already built

        if ASSET_DEBUG:
            print("Rebuilding asset browser UI...")

        # Get filtered and sorted assets
        self.visible_assets = self._filter_and_sort_assets()

        # Limit visible assets for performance
        if len(self.visible_assets) > self.config.max_visible_items:
            self.visible_assets = self.visible_assets[:self.config.max_visible_items]

        # Clear existing UI items
        self.asset_item_uis.clear()

        # Calculate layout based on view mode
        if self.view_mode == AssetViewMode.GRID:
            self._rebuild_grid_layout()
        elif self.view_mode == AssetViewMode.LIST:
            self._rebuild_list_layout()
        else:  # DETAIL
            self._rebuild_detail_layout()

        if ASSET_DEBUG:
            print(f"UI rebuilt: {len(self.visible_assets)} visible assets")

    def _rebuild_grid_layout(self):
        """Rebuild UI in grid layout with configuration support"""
        layout = self.config.layout

        # Calculate grid dimensions
        padding = layout.grid_padding
        available_width = self.rect.width - padding * 2

        # Auto-calculate columns if configured
        if layout.grid_columns == 0:
            min_item_width = layout.grid_item_width
            columns = max(1, available_width // min_item_width)
        else:
            columns = layout.grid_columns

        item_width = available_width // columns
        item_height = layout.grid_item_height

        # Create asset item UIs
        current_y = -self.scroll_y
        for i, asset_id in enumerate(self.visible_assets):
            row = i // columns
            col = i % columns

            x = col * item_width + padding
            y = current_y + row * item_height + padding

            rect = pygame.Rect(x, y, item_width - padding, item_height - padding)

            asset_item_ui = AssetItemUI(self.assets[asset_id], rect, self.config)
            asset_item_ui.is_selected = asset_id in self.selected_assets
            asset_item_ui.is_focused = asset_id == self.focused_asset
            asset_item_ui.is_hovered = asset_id == self.hovered_asset

            self.asset_item_uis.append(asset_item_ui)

        # Update scroll bounds
        if self.visible_assets:
            total_rows = (len(self.visible_assets) + columns - 1) // columns
            self.content_height = total_rows * item_height + padding * 2
        else:
            self.content_height = 0

        self.max_scroll = max(0, self.content_height - self.rect.height)

    def _rebuild_list_layout(self):
        """Rebuild UI in list layout with configuration support"""
        layout = self.config.layout
        item_height = layout.list_item_height

        current_y = -self.scroll_y
        for i, asset_id in enumerate(self.visible_assets):
            y = current_y + i * item_height
            rect = pygame.Rect(0, y, self.rect.width, item_height)

            asset_item_ui = AssetItemUI(self.assets[asset_id], rect, self.config)
            asset_item_ui.is_selected = asset_id in self.selected_assets
            asset_item_ui.is_focused = asset_id == self.focused_asset
            asset_item_ui.is_hovered = asset_id == self.hovered_asset

            self.asset_item_uis.append(asset_item_ui)

        # Update scroll bounds
        self.content_height = len(self.visible_assets) * item_height
        self.max_scroll = max(0, self.content_height - self.rect.height)

    def _rebuild_detail_layout(self):
        """Rebuild UI in detail layout with configuration support"""
        layout = self.config.layout
        item_height = layout.detail_item_height

        current_y = -self.scroll_y
        for i, asset_id in enumerate(self.visible_assets):
            y = current_y + i * item_height
            rect = pygame.Rect(0, y, self.rect.width, item_height)

            asset_item_ui = AssetItemUI(self.assets[asset_id], rect, self.config)
            asset_item_ui.is_selected = asset_id in self.selected_assets
            asset_item_ui.is_focused = asset_id == self.focused_asset
            asset_item_ui.is_hovered = asset_id == self.hovered_asset

            self.asset_item_uis.append(asset_item_ui)

        # Update scroll bounds
        self.content_height = len(self.visible_assets) * item_height
        self.max_scroll = max(0, self.content_height - self.rect.height)

    def _rebuild_image(self):
        """Rebuild the image surface with improved theming and performance"""
        # Fill background
        bg_color = self.theme_manager.get_color('dark_bg')
        if hasattr(bg_color, 'apply_gradient_to_surface'):
            bg_color.apply_gradient_to_surface(self.image)
        else:
            self.image.fill(bg_color)

        # Draw asset items
        items_drawn = 0
        for asset_item_ui in self.asset_item_uis:
            # Only draw visible items
            if (asset_item_ui.rect.bottom >= 0 and
                    asset_item_ui.rect.top < self.rect.height):

                # Create subsurface for this item
                try:
                    # Calculate intersection with panel
                    visible_rect = asset_item_ui.rect.clip(pygame.Rect(0, 0, self.rect.width, self.rect.height))
                    if visible_rect.width > 0 and visible_rect.height > 0:
                        item_surface = self.image.subsurface(visible_rect)

                        # Adjust asset UI rect for drawing
                        old_rect = asset_item_ui.rect
                        asset_item_ui.rect = pygame.Rect(
                            old_rect.x - visible_rect.x,
                            old_rect.y - visible_rect.y,
                            old_rect.width,
                            old_rect.height
                        )

                        # Re-calculate layout for new rect
                        asset_item_ui.calculate_layout()

                        # Draw the asset
                        asset_item_ui.draw(item_surface, self.theme_manager, self.preview_generator)

                        # Restore original rect
                        asset_item_ui.rect = old_rect
                        asset_item_ui.calculate_layout()

                        items_drawn += 1

                except (ValueError, pygame.error) as e:
                    if ASSET_DEBUG:
                        print(f"Error drawing asset item: {e}")

        # Draw grid lines if configured
        if (self.view_mode == AssetViewMode.GRID and
                self.config.layout.show_grid_lines and
                self.asset_item_uis):
            self._draw_grid_lines()

        # Draw border
        border_color = self.theme_manager.get_color('normal_border')
        pygame.draw.rect(self.image, border_color, self.image.get_rect(),
                         self.config.layout.border_width)

        if ASSET_DEBUG and items_drawn > 0:
            print(f"Image rebuilt: Drew {items_drawn} asset items")

    def _draw_grid_lines(self):
        """Draw grid lines for grid layout with configuration support"""
        if not self.asset_item_uis:
            return

        layout = self.config.layout
        grid_color = self.theme_manager.get_color('grid_line')
        line_width = layout.grid_line_width

        # Vertical lines
        if len(self.asset_item_uis) > 1:
            first_item = self.asset_item_uis[0]
            second_item = None

            # Find item in second column
            for item in self.asset_item_uis[1:]:
                if item.rect.x > first_item.rect.x:
                    second_item = item
                    break

            if second_item:
                column_width = second_item.rect.x - first_item.rect.x
                x = first_item.rect.right + layout.grid_padding // 2

                while x < self.rect.width:
                    pygame.draw.line(self.image, grid_color, (x, 0), (x, self.rect.height), line_width)
                    x += column_width

    def process_event(self, event: pygame.event.Event) -> bool:
        """Process pygame events with improved configuration support"""
        consumed = super().process_event(event)
        if consumed:
            return True

        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.rect.collidepoint(event.pos):
                relative_pos = (event.pos[0] - self.rect.x, event.pos[1] - self.rect.y)

                if event.button == 1:  # Left click
                    consumed = self._handle_left_click(relative_pos)
                elif event.button == 3:  # Right click
                    consumed = self._handle_right_click(relative_pos)

        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1:
                consumed = self._handle_mouse_up(event.pos)

        elif event.type == pygame.MOUSEMOTION:
            if self.rect.collidepoint(event.pos):
                relative_pos = (event.pos[0] - self.rect.x, event.pos[1] - self.rect.y)
                consumed = self._handle_mouse_motion(relative_pos)

        elif event.type == pygame.MOUSEWHEEL:
            if self.rect.collidepoint(pygame.mouse.get_pos()):
                consumed = self._handle_scroll(event.y)

        elif event.type == pygame.KEYDOWN:
            consumed = self._handle_key_event(event)

        return consumed

    def _handle_left_click(self, pos: Tuple[int, int]) -> bool:
        """Handle left mouse click with configuration support"""
        clicked_asset = self._get_asset_at_position(pos)

        if clicked_asset:
            # Check for double click
            current_time = pygame.time.get_ticks()
            is_double_click = (current_time - self.last_click_time < self.config.double_click_time and
                               clicked_asset == self.focused_asset)
            self.last_click_time = current_time

            # Handle selection based on configuration
            keys = pygame.key.get_pressed()

            if self.config.behavior.allow_multi_select:
                if keys[pygame.K_LCTRL] or keys[pygame.K_RCTRL]:
                    # Ctrl+click: toggle selection
                    if clicked_asset in self.selected_assets:
                        self.selected_assets.remove(clicked_asset)
                    else:
                        self.selected_assets.add(clicked_asset)
                    # Update both focus and anchor for non-shift clicks
                    self.focused_asset = clicked_asset
                    self.selection_anchor = clicked_asset

                elif keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]:
                    # Shift+click range selection
                    if ASSET_DEBUG:
                        print(f"Shift+click: selection_anchor={self.selection_anchor}, clicked_asset={clicked_asset}")

                    # Use selection_anchor instead of focused_asset
                    if self.selection_anchor and self.selection_anchor in self.visible_assets and clicked_asset in self.visible_assets:
                        try:
                            start_idx = self.visible_assets.index(self.selection_anchor)
                            end_idx = self.visible_assets.index(clicked_asset)

                            if ASSET_DEBUG:
                                print(f"Range indices: start={start_idx}, end={end_idx}")

                            # Make sure we have the right order
                            if start_idx > end_idx:
                                start_idx, end_idx = end_idx, start_idx

                            # Create range selection
                            range_assets = set()
                            for i in range(start_idx, end_idx + 1):
                                if i < len(self.visible_assets):
                                    range_assets.add(self.visible_assets[i])

                            # Set selection to the range
                            self.selected_assets = range_assets

                            # Don't change the anchor on shift+click - keep it for further range selections
                            # Only update focus to the clicked item
                            self.focused_asset = clicked_asset

                            if ASSET_DEBUG:
                                print(
                                    f"Selected range: {len(self.selected_assets)} assets from index {start_idx} to {end_idx}")

                        except ValueError as e:
                            if ASSET_DEBUG:
                                print(f"Range selection failed: {e}")
                            # Fallback to single selection
                            self.selected_assets = {clicked_asset}
                            self.focused_asset = clicked_asset
                            self.selection_anchor = clicked_asset
                    else:
                        # No valid anchor for range selection, do single selection
                        if ASSET_DEBUG:
                            print(f"No valid anchor for range selection, selecting single asset")
                        self.selected_assets = {clicked_asset}
                        self.focused_asset = clicked_asset
                        self.selection_anchor = clicked_asset
                else:
                    # Normal click: single selection
                    self.selected_assets = {clicked_asset}
                    self.focused_asset = clicked_asset
                    self.selection_anchor = clicked_asset  # Update anchor on normal click
            else:
                # Single selection only
                self.selected_assets = {clicked_asset}
                self.focused_asset = clicked_asset
                self.selection_anchor = clicked_asset

            # Fire selection event
            event_data = {
                'asset': self.assets[clicked_asset],
                'selected_assets': [self.assets[aid] for aid in self.selected_assets],
                'ui_element': self
            }
            pygame.event.post(pygame.event.Event(UI_ASSET_SELECTED, event_data))

            # Fire double click event
            if is_double_click:
                event_data = {
                    'asset': self.assets[clicked_asset],
                    'ui_element': self,
                    'action': self.config.behavior.double_click_action
                }
                pygame.event.post(pygame.event.Event(UI_ASSET_DOUBLE_CLICKED, event_data))

                action = self.config.behavior.double_click_action
                asset_name = self.assets[clicked_asset].get_display_name(self.config)
                print(f"Double-click action '{action}' on asset: {asset_name}")

            # Start drag if enabled
            if (self.config.behavior.allow_drag_drop and
                    len(self.selected_assets) > 0):
                self.dragging_assets = self.selected_assets.copy()
                self.drag_start_pos = pos

                event_data = {
                    'assets': [self.assets[aid] for aid in self.dragging_assets],
                    'ui_element': self
                }
                pygame.event.post(pygame.event.Event(UI_ASSET_DRAG_STARTED, event_data))

            # Force rebuild to show selection changes
            self._force_rebuild = True
            self.rebuild_ui()
            self._rebuild_image()
            return True
        else:
            # Click on empty space
            if self.config.behavior.allow_empty_selection:
                self.selected_assets.clear()
                self.focused_asset = None
                # Keep selection_anchor - don't clear it! This is the key fix
                # self.selection_anchor remains unchanged
                self._force_rebuild = True
                self.rebuild_ui()
                self._rebuild_image()
            return True

        return False

    def _handle_right_click(self, pos: Tuple[int, int]) -> bool:
        """Handle right mouse click with configuration support"""
        clicked_asset = self._get_asset_at_position(pos)

        if clicked_asset:
            # Select asset if not already selected and configured to do so
            if (self.config.behavior.right_click_action == "select" or
                    clicked_asset not in self.selected_assets):
                self.selected_assets = {clicked_asset}
                self.focused_asset = clicked_asset
                self._force_rebuild = True
                self.rebuild_ui()
                self._rebuild_image()

            # Fire context menu event
            event_data = {
                'asset': self.assets[clicked_asset],
                'selected_assets': [self.assets[aid] for aid in self.selected_assets],
                'mouse_pos': pos,
                'ui_element': self
            }
            pygame.event.post(pygame.event.Event(UI_ASSET_RIGHT_CLICKED, event_data))

            # Print context menu info
            asset_name = self.assets[clicked_asset].get_display_name(self.config)
            print(f"Right-click context menu for asset: {asset_name}")
            return True

        return False

    def _handle_mouse_up(self, pos: Tuple[int, int]) -> bool:
        """Handle mouse up (end drag)"""
        if self.dragging_assets:
            # End drag operation
            self.dragging_assets.clear()
            self.drag_start_pos = None
            return True
        return False

    def _handle_mouse_motion(self, pos: Tuple[int, int]) -> bool:
        """Handle mouse motion with configuration support"""
        new_hovered = self._get_asset_at_position(pos)

        if new_hovered != self.hovered_asset:
            self.hovered_asset = new_hovered

            # Focus follows mouse if configured
            if self.config.behavior.focus_follows_mouse and new_hovered:
                self.focused_asset = new_hovered

            # Select on hover if configured
            if self.config.behavior.select_on_hover and new_hovered:
                self.selected_assets = {new_hovered}

            self._force_rebuild = True
            self.rebuild_ui()
            self._rebuild_image()
            return True

        # Handle drag motion
        if self.dragging_assets and self.drag_start_pos:
            # Could implement drag preview here
            pass

        return False

    def _handle_scroll(self, delta: int) -> bool:
        """Handle scroll wheel with configuration support"""
        interaction = self.config.interaction

        if self.view_mode == AssetViewMode.GRID:
            scroll_speed = self.config.layout.grid_item_height * interaction.scroll_speed
        else:
            scroll_speed = self.config.layout.list_item_height * interaction.scroll_speed

        old_scroll = self.scroll_y
        self.scroll_y = max(0, min(self.max_scroll, self.scroll_y - delta * scroll_speed))

        if old_scroll != self.scroll_y:
            self._force_rebuild = True
            self.rebuild_ui()
            self._rebuild_image()
            return True

        return False

    def _handle_key_event(self, event: pygame.event.Event) -> bool:
        """Handle keyboard events with configuration support"""
        if not self.visible_assets:
            return False

        if event.key == pygame.K_UP or event.key == pygame.K_DOWN:
            # Navigate assets
            direction = -1 if event.key == pygame.K_UP else 1

            if self.focused_asset and self.focused_asset in self.visible_assets:
                current_idx = self.visible_assets.index(self.focused_asset)
            else:
                current_idx = -1 if direction == 1 else len(self.visible_assets)

            new_idx = max(0, min(len(self.visible_assets) - 1, current_idx + direction))

            if 0 <= new_idx < len(self.visible_assets):
                self.focused_asset = self.visible_assets[new_idx]

                # Update selection if not holding ctrl
                keys = pygame.key.get_pressed()
                if (not (keys[pygame.K_LCTRL] or keys[pygame.K_RCTRL]) and
                        self.config.behavior.allow_multi_select):
                    self.selected_assets = {self.focused_asset}

                self._force_rebuild = True
                self.rebuild_ui()
                self._rebuild_image()
                return True

        elif event.key == pygame.K_RETURN or event.key == pygame.K_SPACE:
            # Activate focused asset
            if self.focused_asset:
                event_data = {
                    'asset': self.assets[self.focused_asset],
                    'ui_element': self,
                    'action': self.config.behavior.double_click_action
                }
                pygame.event.post(pygame.event.Event(UI_ASSET_DOUBLE_CLICKED, event_data))

                # Print activation info
                action = self.config.behavior.double_click_action
                asset_name = self.assets[self.focused_asset].get_display_name(self.config)
                print(f"Keyboard activation '{action}' on asset: {asset_name}")
                return True

        elif event.key == pygame.K_DELETE:
            # Delete selected assets
            if self.selected_assets:
                event_data = {
                    'assets': [self.assets[aid] for aid in self.selected_assets],
                    'ui_element': self
                }
                pygame.event.post(pygame.event.Event(UI_ASSET_EXPORT_REQUESTED, event_data))
                return True

        return False

    def _get_asset_at_position(self, pos: Tuple[int, int]) -> Optional[str]:
        """Get asset at the given position"""
        for asset_item_ui in self.asset_item_uis:
            if asset_item_ui.contains_point(pos):
                return asset_item_ui.asset_item.id
        return None

    def update(self, time_delta: float):
        """Update the panel with configuration support"""
        super().update(time_delta)

        # Update loading indicators if configured
        if (self.config.behavior.show_loading_indicators and
                self.config.behavior.animate_loading):
            has_loading = any(asset.is_loading_thumbnail for asset in self.assets.values())
            if has_loading:
                self._rebuild_image()

    # Public API methods with configuration support
    def add_asset(self, file_path: Union[str, Path], asset_type: AssetType = None,
                  collection_id: str = None) -> AssetItem:
        """Add an asset to the browser"""
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"Asset file not found: {file_path}")

        # Auto-detect asset type if not provided
        if asset_type is None:
            asset_type = self._detect_asset_type(file_path)

        # Generate unique ID
        asset_id = self.generate_asset_id(file_path)

        # Create metadata
        metadata = self._extract_file_metadata(file_path)

        # Create asset item
        asset_item = AssetItem(
            id=asset_id,
            name=file_path.stem,
            file_path=file_path,
            asset_type=asset_type,
            metadata=metadata,
            collection_id=collection_id
        )

        self.assets[asset_id] = asset_item

        # Add to collection if specified
        if collection_id and collection_id in self.collections:
            self.collections[collection_id].add_asset(asset_id)

        # Rebuild UI to show new asset
        self._force_rebuild = True
        self.rebuild_ui()
        self._rebuild_image()

        # Fire event
        event_data = {
            'asset': asset_item,
            'ui_element': self
        }
        pygame.event.post(pygame.event.Event(UI_ASSET_IMPORT_REQUESTED, event_data))

        return asset_item

    def add_collection(self, name: str, description: str = "", parent_id: str = None) -> AssetCollection:
        """Add a new collection"""
        collection_id = self.generate_collection_id(name)

        collection = AssetCollection(
            id=collection_id,
            name=name,
            description=description,
            parent_id=parent_id
        )

        self.collections[collection_id] = collection

        # Fire event
        event_data = {
            'collection': collection,
            'ui_element': self
        }
        pygame.event.post(pygame.event.Event(UI_ASSET_COLLECTION_CHANGED, event_data))

        return collection

    @staticmethod
    def _detect_asset_type(file_path: Path) -> AssetType:
        """Auto-detect asset type from file extension"""
        ext = file_path.suffix.lower()

        image_exts = {'.png', '.jpg', '.jpeg', '.bmp', '.tga', '.gif', '.webp', '.tiff'}
        audio_exts = {'.mp3', '.wav', '.ogg', '.flac', '.aac', '.m4a'}
        video_exts = {'.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv'}
        text_exts = {'.txt', '.md', '.rtf'}
        script_exts = {'.py', '.js', '.html', '.css', '.json', '.xml', '.yml', '.yaml'}
        font_exts = {'.ttf', '.otf', '.woff', '.woff2'}
        model_exts = {'.obj', '.fbx', '.dae', '.3ds', '.blend', '.max'}

        if ext in image_exts:
            return AssetType.IMAGE
        elif ext in audio_exts:
            return AssetType.AUDIO
        elif ext in video_exts:
            return AssetType.VIDEO
        elif ext in text_exts:
            return AssetType.TEXT
        elif ext in script_exts:
            return AssetType.SCRIPT
        elif ext in font_exts:
            return AssetType.FONT
        elif ext in model_exts:
            return AssetType.MODEL
        else:
            return AssetType.OTHER

    def _extract_file_metadata(self, file_path: Path) -> AssetMetadata:
        """Extract metadata from file"""
        metadata = AssetMetadata()

        try:
            stat = file_path.stat()
            metadata.file_size = stat.st_size
            metadata.date_created = stat.st_ctime
            metadata.date_modified = stat.st_mtime

            # Generate file hash for caching
            metadata.file_hash = self._calculate_file_hash(file_path)

            # Extract format-specific metadata
            if file_path.suffix.lower() in {'.png', '.jpg', '.jpeg', '.bmp', '.tga', '.gif'}:
                try:
                    if PIL_AVAILABLE:
                        with PILImage.open(file_path) as img:
                            metadata.width, metadata.height = img.size
                            metadata.format = img.format
                            metadata.color_depth = len(img.getbands()) * 8
                    else:
                        # Fallback to pygame
                        img = pygame.image.load(str(file_path))
                        metadata.width, metadata.height = img.get_size()
                except:
                    pass

        except Exception as e:
            if ASSET_DEBUG:
                print(f"Error extracting metadata for {file_path}: {e}")

        return metadata

    @staticmethod
    def _calculate_file_hash(file_path: Path) -> str:
        """Calculate MD5 hash of file for caching"""
        try:
            hash_md5 = hashlib.md5()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except:
            return str(file_path)  # Fallback to path

    @staticmethod
    def generate_asset_id(file_path: Path) -> str:
        """Generate unique asset ID"""
        return f"asset_{abs(hash(str(file_path)))}"

    def generate_collection_id(self, name: str) -> str:
        """Generate unique collection ID"""
        base_id = f"collection_{name.lower().replace(' ', '_')}"
        counter = 1
        collection_id = base_id

        while collection_id in self.collections:
            collection_id = f"{base_id}_{counter}"
            counter += 1

        return collection_id

    def set_current_collection(self, collection_id: Optional[str]):
        """Set the currently viewed collection"""
        self.current_collection = collection_id
        self._force_rebuild = True
        self.rebuild_ui()
        self._rebuild_image()

    def set_search_query(self, query: str):
        """Set search query and filter assets"""
        self.search_query = query.strip()
        self._force_rebuild = True
        self.rebuild_ui()
        self._rebuild_image()

        # Fire search event
        event_data = {
            'query': self.search_query,
            'ui_element': self
        }
        pygame.event.post(pygame.event.Event(UI_ASSET_SEARCH_UPDATED, event_data))

    def set_view_mode(self, view_mode: AssetViewMode):
        """Change view mode"""
        if self.view_mode != view_mode:
            self.view_mode = view_mode
            self.config.default_view_mode = view_mode  # Update config
            self._force_rebuild = True
            self.rebuild_ui()
            self._rebuild_image()

    def get_selected_assets(self) -> List[AssetItem]:
        """Get currently selected assets"""
        return [self.assets[aid] for aid in self.selected_assets if aid in self.assets]

    def select_asset(self, asset_id: str):
        """Programmatically select an asset"""
        if asset_id in self.assets:
            self.selected_assets = {asset_id}
            self.focused_asset = asset_id
            self._force_rebuild = True
            self.rebuild_ui()
            self._rebuild_image()

    def clear_selection(self):
        """Clear asset selection"""
        self.selected_assets.clear()
        self.focused_asset = None
        self._force_rebuild = True
        self.rebuild_ui()
        self._rebuild_image()

    def remove_asset(self, asset_id: str):
        """Remove an asset"""
        if asset_id in self.assets:
            # Remove from collections
            for collection in self.collections.values():
                collection.remove_asset(asset_id)

            # Remove from selection
            self.selected_assets.discard(asset_id)
            if self.focused_asset == asset_id:
                self.focused_asset = None

            # Remove asset
            del self.assets[asset_id]

            self._force_rebuild = True
            self.rebuild_ui()
            self._rebuild_image()

    def refresh(self):
        """Refresh the asset browser"""
        self._force_rebuild = True
        self.rebuild_ui()
        self._rebuild_image()

    # Configuration update methods
    def update_layout_config(self, layout_config: AssetLayoutConfig):
        """Update layout configuration and rebuild"""
        import copy
        self.config.layout = copy.deepcopy(layout_config)
        self._force_rebuild = True  # Force rebuild
        self.rebuild_ui()
        self._rebuild_image()
        print(
            f"Layout config updated - grid size: {self.config.layout.grid_item_width}x{self.config.layout.grid_item_height}")

    def update_behavior_config(self, behavior_config: AssetBehaviorConfig):
        """Update behavior configuration"""
        import copy
        self.config.behavior = copy.deepcopy(behavior_config)
        self._force_rebuild = True  # Force rebuild
        self.rebuild_ui()
        self._rebuild_image()
        print(f"Behavior config updated - metadata overlay: {self.config.behavior.show_metadata_overlay}")

    def update_interaction_config(self, interaction_config: AssetInteractionConfig):
        """Update interaction configuration"""
        import copy
        self.config.interaction = copy.deepcopy(interaction_config)

    def save_metadata_to_file(self, file_path: Union[str, Path]):
        """Save asset metadata to JSON file"""
        try:
            data = {
                'assets': {
                    aid: {
                        'name': asset.name,
                        'file_path': str(asset.file_path),
                        'asset_type': asset.asset_type.value,
                        'metadata': asset.metadata.to_dict(),
                        'collection_id': asset.collection_id
                    }
                    for aid, asset in self.assets.items()
                },
                'collections': {
                    cid: {
                        'name': collection.name,
                        'description': collection.description,
                        'asset_ids': list(collection.asset_ids),
                        'parent_id': collection.parent_id,
                    }
                    for cid, collection in self.collections.items()
                }
            }

            with open(file_path, 'w') as f:
                json.dump(data, f, indent=2)

        except Exception as e:
            if ASSET_DEBUG:
                print(f"Error saving metadata: {e}")

    def load_metadata_from_file(self, file_path: Union[str, Path]):
        """Load asset metadata from JSON file"""
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)

            # Load assets
            for aid, asset_data in data.get('assets', {}).items():
                file_path_obj = Path(asset_data['file_path'])
                if file_path_obj.exists():
                    asset_type = AssetType(asset_data['asset_type'])
                    metadata = AssetMetadata.from_dict(asset_data['metadata'])

                    asset = AssetItem(
                        id=aid,
                        name=asset_data['name'],
                        file_path=file_path_obj,
                        asset_type=asset_type,
                        metadata=metadata,
                        collection_id=asset_data.get('collection_id')
                    )

                    self.assets[aid] = asset

            # Load collections
            for cid, collection_data in data.get('collections', {}).items():
                collection = AssetCollection(
                    id=cid,
                    name=collection_data['name'],
                    description=collection_data['description'],
                    asset_ids=set(collection_data.get('asset_ids', [])),
                    parent_id=collection_data.get('parent_id'),
                )

                self.collections[cid] = collection

            self._force_rebuild = True
            self.rebuild_ui()
            self._rebuild_image()

        except Exception as e:
            if ASSET_DEBUG:
                print(f"Error loading metadata: {e}")


# Example theme for asset browser with comprehensive styling
ASSET_BROWSER_THEME = {
    "asset_browser": {
        "colours": {
            "dark_bg": "#2a2a2a",
            "normal_text": "#ffffff",
            "secondary_text": "#b0b0b0",
            "disabled_text": "#808080",
            "selected_bg": "#4a90e2",
            "hovered_bg": "#404040",
            "focused_bg": "#5aa3f0",
            "normal_border": "#646464",
            "focus_border": "#ffffff",
            "selection_border": "#78a0ff",
            "thumbnail_border": "#505050",
            "grid_line": "#505050",
            "loading_indicator": "#64c864",
            "accent": "#64c864",
            "error": "#c86464",
            "warning": "#c8c864",
            "success": "#64c864",
            "placeholder_bg": "#323232",
            "metadata_bg": "#1e1e1e80",
        },
        "font": {
            "name": "arial",
            "size": "11",
            "bold": "0",
            "italic": "0"
        }
    }
}


def create_sample_assets(browser: AssetBrowserPanel) -> None:
    """Create sample assets for demonstration"""

    # Create some collections
    images_collection = browser.add_collection("Images", "Image assets")
    audio_collection = browser.add_collection("Audio", "Sound effects and music")
    documents_collection = browser.add_collection("Documents", "Text documents")

    # Create sample assets (these would normally be real files)
    sample_assets = [
        ("logo.png", AssetType.IMAGE, images_collection.id),
        ("background.jpg", AssetType.IMAGE, images_collection.id),
        ("character_sprite.png", AssetType.IMAGE, images_collection.id),
        ("explosion.wav", AssetType.AUDIO, audio_collection.id),
        ("background_music.ogg", AssetType.AUDIO, audio_collection.id),
        ("readme.txt", AssetType.TEXT, documents_collection.id),
        ("config.json", AssetType.SCRIPT, documents_collection.id),
        ("shader.glsl", AssetType.SCRIPT, None),
        ("font.ttf", AssetType.FONT, None),
    ]

    for name, asset_type, collection_id in sample_assets:
        # Create temporary file path (in real usage these would be actual files)
        temp_path = Path(f"temp_assets/{name}")

        # Create fake metadata
        metadata = AssetMetadata()
        metadata.file_size = hash(name) % 100000 + 1000  # Fake file size
        metadata.date_created = time.time() - (hash(name) % 10000)
        metadata.date_modified = time.time() - (hash(name) % 5000)

        if asset_type == AssetType.IMAGE:
            metadata.width = 256 + (hash(name) % 512)
            metadata.height = 256 + (hash(name[::-1]) % 512)
            metadata.format = "PNG" if name.endswith('.png') else "JPEG"

        # Add some sample tags
        if "sprite" in name:
            metadata.tags.add("character")
            metadata.tags.add("game")
        elif "background" in name:
            metadata.tags.add("environment")
        elif "explosion" in name:
            metadata.tags.add("sfx")
            metadata.tags.add("action")

        # Sample rating
        metadata.rating = hash(name) % 6  # 0-5 stars

        # Create asset item directly (since files don't exist)
        asset_id = browser.generate_asset_id(temp_path)
        asset = AssetItem(
            id=asset_id,
            name=Path(name).stem,
            file_path=temp_path,
            asset_type=asset_type,
            metadata=metadata,
            collection_id=collection_id
        )

        browser.assets[asset_id] = asset

        # Add to collection
        if collection_id and collection_id in browser.collections:
            browser.collections[collection_id].add_asset(asset_id)


def main():
    """Example demonstration of the Asset Browser Panel"""
    pygame.init()
    screen = pygame.display.set_mode((1200, 800))
    pygame.display.set_caption("Configurable Asset Browser Panel Demo")
    clock = pygame.time.Clock()

    # Create manager with theme
    manager = pygame_gui.UIManager((1200, 800), ASSET_BROWSER_THEME)

    # Create different configurations for demonstration
    compact_config = AssetConfig()
    compact_config.layout.grid_item_width = 120
    compact_config.layout.grid_item_height = 140
    compact_config.layout.grid_thumbnail_size = (96, 96)
    compact_config.behavior.show_metadata_overlay = False
    compact_config.behavior.show_file_extensions = True

    large_config = AssetConfig()
    large_config.layout.grid_item_width = 200
    large_config.layout.grid_item_height = 220
    large_config.layout.grid_thumbnail_size = (160, 160)
    large_config.behavior.show_metadata_overlay = True
    large_config.behavior.show_tooltips = True
    large_config.layout.show_grid_lines = True

    # Create asset browser with compact config initially
    asset_browser = AssetBrowserPanel(
        pygame.Rect(50, 50, 800, 600),
        manager,
        compact_config,
        object_id=ObjectID(object_id='#main_browser', class_id='@asset_panel')
    )

    # Create sample assets FIRST
    create_sample_assets(asset_browser)

    # FORCE initial rebuild to show assets
    asset_browser._force_rebuild = True
    asset_browser.rebuild_ui()
    asset_browser._rebuild_image()

    # Instructions
    print("\nConfigurable Asset Browser Panel Demo")
    print("\nControls:")
    print("- Click assets to select")
    print("- Ctrl+click for multi-select")
    print("- Shift+click for range select")
    print("- Double-click to activate (shows action)")
    print("- Right-click for context menu (shows message)")
    print("- Arrow keys to navigate")
    print("- Mouse wheel to scroll")

    print("\nConfiguration Controls:")
    print("Press 'C' for compact layout")
    print("Press 'L' for large layout")
    print("Press 'G' for Grid view, 'V' for List view, 'D' for Detail view")
    print("Press '1-3' to switch collections")
    print("Press 'S' to toggle search simulation")
    print("Press 'M' to toggle metadata overlay")
    print("Press 'E' to toggle file extensions")
    print("Press 'T' to toggle theme colors\n")

    # State variables
    collections = list(asset_browser.collections.keys())
    search_active = False
    current_config = "compact"

    running = True
    while running:
        time_delta = clock.tick(60) / 1000.0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_c:
                    # Switch to compact layout
                    asset_browser.update_layout_config(compact_config.layout)
                    asset_browser.update_behavior_config(compact_config.behavior)
                    current_config = "compact"
                    print("Switched to compact layout")

                elif event.key == pygame.K_l:
                    # Switch to large layout
                    asset_browser.update_layout_config(large_config.layout)
                    asset_browser.update_behavior_config(large_config.behavior)
                    current_config = "large"
                    print("Switched to large layout")

                elif event.key == pygame.K_g:
                    # Switch to grid view
                    asset_browser.set_view_mode(AssetViewMode.GRID)
                    print("Switched to Grid view")

                elif event.key == pygame.K_v:
                    # Switch to list view
                    asset_browser.set_view_mode(AssetViewMode.LIST)
                    print("Switched to List view")

                elif event.key == pygame.K_d:
                    # Switch to detail view
                    asset_browser.set_view_mode(AssetViewMode.DETAIL)
                    print("Switched to Detail view")

                elif event.key == pygame.K_1:
                    # Show all assets
                    asset_browser.set_current_collection(None)
                    print("Showing all assets")

                elif event.key == pygame.K_2:
                    # Show first collection
                    if collections:
                        asset_browser.set_current_collection(collections[0])
                        collection_name = asset_browser.collections[collections[0]].name
                        print(f"Showing collection: {collection_name}")

                elif event.key == pygame.K_3:
                    # Show second collection
                    if len(collections) > 1:
                        asset_browser.set_current_collection(collections[1])
                        collection_name = asset_browser.collections[collections[1]].name
                        print(f"Showing collection: {collection_name}")

                elif event.key == pygame.K_s:
                    # Toggle search
                    search_active = not search_active
                    if search_active:
                        asset_browser.set_search_query("background")
                        print("Search activated: 'background'")
                    else:
                        asset_browser.set_search_query("")
                        print("Search cleared")

                elif event.key == pygame.K_m:
                    # Toggle metadata overlay
                    current_show_metadata = asset_browser.config.behavior.show_metadata_overlay
                    asset_browser.config.behavior.show_metadata_overlay = not current_show_metadata
                    asset_browser._force_rebuild = True
                    asset_browser.rebuild_ui()
                    asset_browser._rebuild_image()
                    print(f"Metadata overlay: {'ON' if not current_show_metadata else 'OFF'}")

                elif event.key == pygame.K_e:
                    # Toggle file extensions
                    current_show_ext = asset_browser.config.behavior.show_file_extensions
                    asset_browser.config.behavior.show_file_extensions = not current_show_ext
                    asset_browser._force_rebuild = True
                    asset_browser.rebuild_ui()
                    asset_browser._rebuild_image()
                    print(f"File extensions: {'ON' if not current_show_ext else 'OFF'}")

                elif event.key == pygame.K_t:
                    # Toggle theme colors
                    theme_manager = asset_browser.theme_manager

                    if not hasattr(asset_browser, 'is_light_theme'):
                        asset_browser.is_light_theme = False

                    if not asset_browser.is_light_theme:
                        # Switch to lighter theme
                        theme_manager.themed_colors['dark_bg'] = pygame.Color(80, 80, 80)
                        theme_manager.themed_colors['selected_bg'] = pygame.Color(120, 160, 200)
                        theme_manager.themed_colors['hovered_bg'] = pygame.Color(100, 100, 100)
                        theme_manager.themed_colors['normal_text'] = pygame.Color(0, 0, 0)
                        theme_manager.themed_colors['secondary_text'] = pygame.Color(60, 60, 60)
                        asset_browser.is_light_theme = True
                        print("Switched to light theme")
                    else:
                        # Switch back to dark theme
                        theme_manager.themed_colors['dark_bg'] = pygame.Color(42, 42, 42)
                        theme_manager.themed_colors['selected_bg'] = pygame.Color(74, 144, 226)
                        theme_manager.themed_colors['hovered_bg'] = pygame.Color(64, 64, 64)
                        theme_manager.themed_colors['normal_text'] = pygame.Color(255, 255, 255)
                        theme_manager.themed_colors['secondary_text'] = pygame.Color(176, 176, 176)
                        asset_browser.is_light_theme = False
                        print("Switched to dark theme")

                    asset_browser._rebuild_image()

                elif event.key == pygame.K_r:
                    # Reset configuration to defaults
                    default_config = AssetConfig()
                    asset_browser.config = default_config
                    asset_browser.set_view_mode(AssetViewMode.GRID)
                    current_config = "default"
                    print("Reset to default configuration")

                elif event.key == pygame.K_i:
                    # Show info about selected assets
                    selected = asset_browser.get_selected_assets()
                    if selected:
                        print(f"\nSelected Assets ({len(selected)}):")
                        for asset in selected[:5]:  # Show first 5
                            print(f"  {asset.get_display_name(asset_browser.config)}")
                            print(f"    Type: {asset.asset_type.value}")
                            print(f"    Size: {asset.get_file_size_str()}")
                            if asset.metadata.tags:
                                print(f"    Tags: {', '.join(asset.metadata.tags)}")
                            if asset.metadata.rating > 0:
                                stars = "*" * asset.metadata.rating + "_" * (5 - asset.metadata.rating)
                                print(f"    Rating: {stars}")
                            print()
                        if len(selected) > 5:
                            print(f"    ... and {len(selected) - 5} more")
                    else:
                        print("No assets selected")

                # Handle asset browser events with improved messaging
                elif event.type == UI_ASSET_SELECTED:
                    asset = event.asset
                    selected_count = len(event.selected_assets)
                    if ASSET_DEBUG:
                        print(
                            f"Asset selected: {asset.get_display_name(asset_browser.config)} ({selected_count} total selected)")

                elif event.type == UI_ASSET_DOUBLE_CLICKED:
                    asset = event.asset
                    action = event.dict.get('action', 'unknown')
                    print(f"Asset double-clicked: {asset.get_display_name(asset_browser.config)} (Action: {action})")

                    # Show what the action would do
                    if action == "open":
                        print("  -> Would open asset in default application")
                    elif action == "edit":
                        print("  -> Would open asset in edit mode")
                    elif action == "select":
                        print("  -> Would select asset (already done)")

            elif event.type == UI_ASSET_RIGHT_CLICKED:
                asset = event.asset
                print(f"Asset right-clicked: {asset.get_display_name(asset_browser.config)}")
                print("  -> Context menu would show options like:")
                print("     - Open")
                print("     - Edit")
                print("     - Delete")
                print("     - Properties")
                print("     - Add to Collection")

            elif event.type == UI_ASSET_DRAG_STARTED:
                assets = event.assets
                asset_names = [asset.get_display_name(asset_browser.config) for asset in assets[:3]]
                if len(assets) > 3:
                    asset_names.append(f"... and {len(assets) - 3} more")
                print(f"Drag started with {len(assets)} asset(s): {', '.join(asset_names)}")

            elif event.type == UI_ASSET_SEARCH_UPDATED:
                query = event.query
                if ASSET_DEBUG:
                    print(f"Search updated: '{query}'")

            elif event.type == UI_ASSET_COLLECTION_CHANGED:
                collection = event.collection
                print(f"Collection changed: {collection.name}")

            elif event.type == UI_ASSET_EXPORT_REQUESTED:
                assets = event.assets
                print(f"Delete requested for {len(assets)} asset(s)")
                for asset in assets[:3]:
                    print(f"  - {asset.get_display_name(asset_browser.config)}")
                if len(assets) > 3:
                    print(f"  ... and {len(assets) - 3} more")

            # Forward events to manager
            manager.process_events(event)
        # Update
        manager.update(time_delta)

        # Draw
        screen.fill((30, 30, 30))

        # Draw demo info
        font = pygame.font.Font(None, 24)
        info_text = font.render("Asset Browser Demo", True, pygame.Color(255, 255, 255))
        screen.blit(info_text, (900, 50))

        # Show current state
        y_offset = 100
        info_font = pygame.font.Font(None, 18)

        # Configuration info
        config_info = [
            f"Configuration: {current_config.title()}",
            f"View Mode: {asset_browser.view_mode.value.title()}",
            f"Grid Size: {asset_browser.config.layout.grid_item_width}x{asset_browser.config.layout.grid_item_height}",
            f"Thumbnail Size: {asset_browser.config.layout.grid_thumbnail_size}",
            f"Show Metadata: {'Yes' if asset_browser.config.behavior.show_metadata_overlay else 'No'}",
            f"Show Extensions: {'Yes' if asset_browser.config.behavior.show_file_extensions else 'No'}",
            f"Multi-Select: {'Yes' if asset_browser.config.behavior.allow_multi_select else 'No'}",
            f"Grid Lines: {'Yes' if asset_browser.config.layout.show_grid_lines else 'No'}",
        ]

        for i, info in enumerate(config_info):
            color = pygame.Color(200, 200, 200)
            text = info_font.render(info, True, color)
            screen.blit(text, (900, y_offset + i * 22))

        y_offset += len(config_info) * 22 + 10

        # Current collection
        if asset_browser.current_collection:
            collection_name = asset_browser.collections[asset_browser.current_collection].name
            collection_text = f"Collection: {collection_name}"
        else:
            collection_text = "Collection: All Assets"
        text = info_font.render(collection_text, True, pygame.Color(200, 200, 200))
        screen.blit(text, (900, y_offset))
        y_offset += 25

        # Search query
        if asset_browser.search_query:
            search_text = f"Search: '{asset_browser.search_query}'"
            text = info_font.render(search_text, True, pygame.Color(200, 200, 200))
            screen.blit(text, (900, y_offset))
            y_offset += 25

        # Asset count
        total_assets = len(asset_browser.assets)
        visible_assets = len(asset_browser.visible_assets)
        count_text = f"Assets: {visible_assets} / {total_assets}"
        text = info_font.render(count_text, True, pygame.Color(200, 200, 200))
        screen.blit(text, (900, y_offset))
        y_offset += 25

        # Selection count
        selected_count = len(asset_browser.selected_assets)
        if selected_count > 0:
            selection_text = f"Selected: {selected_count}"
            text = info_font.render(selection_text, True, pygame.Color(100, 255, 100))
            screen.blit(text, (900, y_offset))
            y_offset += 25

        # Performance info
        y_offset += 10
        perf_info = [
            f"Max Visible: {asset_browser.config.max_visible_items}",
            f"Cache Size: {asset_browser.config.interaction.thumbnail_cache_size}",
            f"Lazy Loading: {'Yes' if asset_browser.config.behavior.lazy_loading else 'No'}",
            f"Background Gen: {'Yes' if asset_browser.config.behavior.enable_background_loading else 'No'}",
        ]

        perf_text = info_font.render("Performance Settings:", True, pygame.Color(255, 255, 255))
        screen.blit(perf_text, (900, y_offset))
        y_offset += 20

        for info in perf_info:
            text = info_font.render(f"  {info}", True, pygame.Color(180, 180, 180))
            screen.blit(text, (900, y_offset))
            y_offset += 18

        # Collections info
        y_offset += 10
        collections_text = "Collections:"
        text = info_font.render(collections_text, True, pygame.Color(255, 255, 255))
        screen.blit(text, (900, y_offset))
        y_offset += 20

        for i, (cid, collection) in enumerate(asset_browser.collections.items()):
            asset_count = len(collection.asset_ids)
            collection_info = f"  {collection.name} ({asset_count})"

            color = pygame.Color(150, 255, 150) if cid == asset_browser.current_collection else pygame.Color(180,
                                                                                                             180,
                                                                                                             180)
            text = info_font.render(collection_info, True, color)
            screen.blit(text, (900, y_offset))
            y_offset += 18

        # Asset type distribution
        y_offset += 10
        type_counts = {}
        for asset in asset_browser.assets.values():
            type_counts[asset.asset_type] = type_counts.get(asset.asset_type, 0) + 1

        types_text = "Asset Types:"
        text = info_font.render(types_text, True, pygame.Color(255, 255, 255))
        screen.blit(text, (900, y_offset))
        y_offset += 20

        for asset_type, count in sorted(type_counts.items()):
            type_info = f"  {asset_type.value.title()}: {count}"
            text = info_font.render(type_info, True, pygame.Color(180, 180, 180))
            screen.blit(text, (900, y_offset))
            y_offset += 18

        manager.draw_ui(screen)
        pygame.display.flip()

    # Cleanup
    asset_browser.preview_generator.stop()
    pygame.quit()

if __name__ == "__main__":
    main()