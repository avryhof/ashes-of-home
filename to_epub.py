#!/usr/bin/env python3
"""
Markdown to EPUB Converter

This script converts Markdown files to EPUB format for e-readers like Kindle.
Supports multiple input files, custom metadata, and table of contents generation.

Requirements:
    pip install ebooklib markdown beautifulsoup4 Pillow

Usage:
    python markdown_to_epub.py input.md
    python markdown_to_epub.py --title "My Book" --author "John Doe" input.md output.epub
    python markdown_to_epub.py --batch directory/ --output mybook.epub
"""

import argparse
import re
import sys
import uuid
from datetime import datetime
from pathlib import Path

import markdown
from ebooklib import epub


class MarkdownToEpubConverter:
    def __init__(self, title=None, author=None, language='en', cover_image=None):
        self.title = title or "Untitled Book"
        self.author = author or "Unknown Author"
        self.language = language
        self.cover_image = cover_image
        self.chapters = []
        self.toc = []
        self.spine = ['nav']

        # Markdown extensions for better conversion
        self.md_extensions = [
            'markdown.extensions.extra',  # Tables, footnotes, etc.
            'markdown.extensions.codehilite',  # Code highlighting
            'markdown.extensions.toc',  # Table of contents
            'markdown.extensions.tables',  # Table support
            'markdown.extensions.fenced_code'  # Fenced code blocks
        ]

    def extract_title_from_content(self, content):
        """Extract title from first H1 heading if no title provided."""
        lines = content.split('\n')
        for line in lines:
            line = line.strip()
            if line.startswith('# '):
                return line[2:].strip()
        return None

    def split_into_chapters(self, content):
        """Split markdown content into chapters based on H1 headers."""
        # Split by H1 headers (# Title)
        chapters = re.split(r'\n(?=^# .+$)', content, flags=re.MULTILINE)

        # Clean up empty chapters
        chapters = [chapter.strip() for chapter in chapters if chapter.strip()]

        # If no H1 headers found, treat entire content as one chapter
        if len(chapters) == 1 and not chapters[0].startswith('#'):
            return [f"# {self.title}\n\n{chapters[0]}"]

        return chapters

    def markdown_to_html(self, markdown_content):
        """Convert markdown to HTML."""
        md = markdown.Markdown(extensions=self.md_extensions)
        html = md.convert(markdown_content)

        # Wrap in proper HTML structure
        html_template = f"""
        <!DOCTYPE html>
        <html xmlns="http://www.w3.org/1999/xhtml">
        <head>
            <title>{self.title}</title>
            <meta charset="utf-8"/>
            <style>
                body {{
                    font-family: serif;
                    line-height: 1.6;
                    margin: 2em;
                }}
                h1, h2, h3, h4, h5, h6 {{
                    color: #333;
                    margin-top: 1.5em;
                }}
                h1 {{
                    border-bottom: 2px solid #333;
                    padding-bottom: 0.3em;
                }}
                code {{
                    background-color: #f5f5f5;
                    padding: 0.2em 0.4em;
                    border-radius: 3px;
                    font-family: monospace;
                }}
                pre {{
                    background-color: #f5f5f5;
                    padding: 1em;
                    border-radius: 5px;
                    overflow-x: auto;
                }}
                blockquote {{
                    border-left: 4px solid #ddd;
                    margin: 1em 0;
                    padding-left: 1em;
                    color: #666;
                }}
                table {{
                    border-collapse: collapse;
                    width: 100%;
                    margin: 1em 0;
                }}
                th, td {{
                    border: 1px solid #ddd;
                    padding: 0.5em;
                    text-align: left;
                }}
                th {{
                    background-color: #f5f5f5;
                    font-weight: bold;
                }}
            </style>
        </head>
        <body>
        {html}
        </body>
        </html>
        """

        return html_template

    def extract_chapter_title(self, chapter_content):
        """Extract chapter title from first heading."""
        lines = chapter_content.split('\n')
        for line in lines:
            line = line.strip()
            if line.startswith('#'):
                # Remove markdown heading syntax
                title = re.sub(r'^#+\s*', '', line).strip()
                return title
        return f"Chapter {len(self.chapters) + 1}"

    def add_chapter_from_markdown(self, markdown_content, chapter_title=None):
        """Add a chapter from markdown content."""
        if not chapter_title:
            chapter_title = self.extract_chapter_title(markdown_content)

        html_content = self.markdown_to_html(markdown_content)

        # Create chapter
        chapter = epub.EpubHtml(
            title=chapter_title,
            file_name=f'chapter_{len(self.chapters) + 1}.xhtml',
            lang=self.language
        )
        chapter.content = html_content

        self.chapters.append(chapter)
        self.toc.append(chapter)
        self.spine.append(chapter)

        return chapter

    def process_markdown_file(self, file_path):
        """Process a single markdown file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Extract title from content if not set
            if self.title == "Untitled Book":
                extracted_title = self.extract_title_from_content(content)
                if extracted_title:
                    self.title = extracted_title

            # Split into chapters if multiple H1 headers exist
            chapters = self.split_into_chapters(content)

            for chapter_content in chapters:
                self.add_chapter_from_markdown(chapter_content)

        except Exception as e:
            raise Exception(f"Error processing {file_path}: {str(e)}")

    def process_multiple_files(self, file_paths):
        """Process multiple markdown files as separate chapters."""
        for file_path in sorted(file_paths):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Use filename as chapter title if no H1 found
                chapter_title = self.extract_chapter_title(content)
                if chapter_title.startswith('Chapter'):
                    chapter_title = Path(file_path).stem.replace('_', ' ').replace('-', ' ').title()

                self.add_chapter_from_markdown(content, chapter_title)

            except Exception as e:
                print(f"Warning: Error processing {file_path}: {str(e)}")

    def add_cover_image(self, book):
        """Add cover image if provided."""
        if self.cover_image and Path(self.cover_image).exists():
            try:
                with open(self.cover_image, 'rb') as f:
                    cover_content = f.read()

                cover_extension = Path(self.cover_image).suffix.lower()
                media_type = {
                    '.jpg': 'image/jpeg',
                    '.jpeg': 'image/jpeg',
                    '.png': 'image/png',
                    '.gif': 'image/gif'
                }.get(cover_extension, 'image/jpeg')

                book.set_cover(f"cover{cover_extension}", cover_content)

            except Exception as e:
                print(f"Warning: Could not add cover image: {str(e)}")

    def create_epub(self, output_path):
        """Create the EPUB file."""
        if not self.chapters:
            raise ValueError("No chapters to convert. Please check your input files.")

        # Create book
        book = epub.EpubBook()

        # Set metadata
        book.set_identifier(str(uuid.uuid4()))
        book.set_title(self.title)
        book.set_language(self.language)
        book.add_author(self.author)
        book.add_metadata('DC', 'creator', self.author)
        book.add_metadata('DC', 'date', datetime.now().strftime('%Y-%m-%d'))

        # Add cover image
        self.add_cover_image(book)

        # Add chapters
        for chapter in self.chapters:
            book.add_item(chapter)

        # Add default CSS
        style = """
        body { font-family: serif; line-height: 1.6; margin: 2em; }
        h1, h2, h3, h4, h5, h6 { color: #333; margin-top: 1.5em; }
        h1 { border-bottom: 2px solid #333; padding-bottom: 0.3em; }
        code { background-color: #f5f5f5; padding: 0.2em 0.4em; border-radius: 3px; }
        pre { background-color: #f5f5f5; padding: 1em; border-radius: 5px; overflow-x: auto; }
        blockquote { border-left: 4px solid #ddd; margin: 1em 0; padding-left: 1em; color: #666; }
        """
        nav_css = epub.EpubItem(
            uid="nav_css",
            file_name="style/nav.css",
            media_type="text/css",
            content=style
        )
        book.add_item(nav_css)

        # Create table of contents
        book.toc = self.toc

        # Add navigation
        book.add_item(epub.EpubNcx())
        book.add_item(epub.EpubNav())

        # Set spine
        book.spine = self.spine

        # Create EPUB file
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        epub.write_epub(str(output_path), book)

        return output_path


def convert_single_file(input_path, output_path=None, title=None, author=None,
                        language='en', cover_image=None):
    """Convert a single markdown file to EPUB."""
    input_path = Path(input_path)

    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    if not input_path.suffix.lower() in ['.md', '.markdown', '.txt']:
        raise ValueError("Input file must be a markdown file (.md, .markdown, or .txt)")

    # Generate output path if not provided
    if output_path is None:
        output_path = input_path.with_suffix('.epub')
    else:
        output_path = Path(output_path)

    # Use filename as title if not provided
    if not title:
        title = input_path.stem.replace('_', ' ').replace('-', ' ').title()

    # Convert
    converter = MarkdownToEpubConverter(
        title=title,
        author=author,
        language=language,
        cover_image=cover_image
    )
    converter.process_markdown_file(input_path)
    result_path = converter.create_epub(output_path)

    print(f"Converted: {input_path} -> {result_path}")
    return result_path


def convert_batch(directory_path, output_path=None, title=None, author=None,
                  language='en', cover_image=None):
    """Convert all markdown files in a directory to a single EPUB."""
    directory = Path(directory_path)

    if not directory.exists():
        raise FileNotFoundError(f"Directory not found: {directory}")

    if not directory.is_dir():
        raise ValueError(f"Path is not a directory: {directory}")

    # Find markdown files
    md_files = list(directory.glob('*.md')) + list(directory.glob('*.markdown'))

    if not md_files:
        print(f"No markdown files found in {directory}")
        return

    # Generate output path if not provided
    if output_path is None:
        output_path = directory / f"{directory.name}.epub"
    else:
        output_path = Path(output_path)

    # Use directory name as title if not provided
    if not title:
        title = directory.name.replace('_', ' ').replace('-', ' ').title()

    # Convert
    converter = MarkdownToEpubConverter(
        title=title,
        author=author,
        language=language,
        cover_image=cover_image
    )
    converter.process_multiple_files(md_files)
    result_path = converter.create_epub(output_path)

    print(f"Converted {len(md_files)} files to: {result_path}")
    return result_path


def main():
    parser = argparse.ArgumentParser(
        description="Convert Markdown files to EPUB format",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s document.md                                    # Convert single file
  %(prog)s document.md --title "My Book" --author "John" # With metadata
  %(prog)s --batch ./chapters/ --output mybook.epub      # Combine multiple files
  %(prog)s book.md --cover cover.jpg                      # With cover image
        """
    )

    parser.add_argument('input', help='Input markdown file or directory (with --batch)')
    parser.add_argument('output', nargs='?', help='Output EPUB file (optional)')
    parser.add_argument('--batch', action='store_true',
                        help='Combine all markdown files in directory into one EPUB')
    parser.add_argument('--title', help='Book title')
    parser.add_argument('--author', help='Book author')
    parser.add_argument('--language', default='en', help='Book language (default: en)')
    parser.add_argument('--cover', help='Cover image file (JPG, PNG, GIF)')

    args = parser.parse_args()

    try:
        if args.batch:
            convert_batch(
                args.input,
                args.output,
                args.title,
                args.author,
                args.language,
                args.cover
            )
        else:
            convert_single_file(
                args.input,
                args.output,
                args.title,
                args.author,
                args.language,
                args.cover
            )

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
