"""
Travel-domain document chunkers with specific strategies for different content types.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
import re
import logging

logger = logging.getLogger("backend.rag.chunkers")


@dataclass
class DocumentChunk:
    """A chunk of a document with content and metadata."""
    id: str
    content: str
    metadata: Dict[str, Any]
    start_index: int = 0
    end_index: int = 0


def count_tokens(text: str) -> int:
    """Approximate token count using simple heuristics."""
    try:
        import tiktoken
        encoder = tiktoken.get_encoding("cl100k_base")  # Claude-Opus encoding
        return len(encoder.encode(text))
    except ImportError:
        # Fallback: rough approximation (1 token ≈ 4 characters)
        return len(text) // 4


class DocumentChunker(ABC):
    """Abstract base class for document chunkers."""

    def __init__(
        self,
        chunk_size: int = 600,
        chunk_overlap: int = 50,
        min_chunk_size: int = 100
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size

    @abstractmethod
    def chunk_document(
        self,
        content: str,
        document_id: str,
        metadata: Dict[str, Any]
    ) -> List[DocumentChunk]:
        """Chunk a document into smaller pieces."""
        ...


class SentenceBoundaryChunker(DocumentChunker):
    """General-purpose chunker that respects sentence boundaries."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Regex for sentence endings (with some travel-specific exceptions)
        self.sentence_pattern = re.compile(
            r'(?<![A-Z][a-z]\.)\s*[.!?]\s+(?=[A-Z])'  # Avoid splitting on "Mr.", "St.", "Dr."
        )

    def chunk_document(
        self,
        content: str,
        document_id: str,
        metadata: Dict[str, Any]
    ) -> List[DocumentChunk]:
        """Chunk text by sentences while respecting token limits."""
        sentences = self.sentence_pattern.split(content)
        chunks = []
        current_chunk = ""
        current_start = 0
        chunk_counter = 0

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            # Check if adding this sentence would exceed chunk size
            potential_chunk = f"{current_chunk} {sentence}".strip()

            if count_tokens(potential_chunk) <= self.chunk_size:
                current_chunk = potential_chunk
            else:
                # Save current chunk if it meets minimum size
                if current_chunk and count_tokens(current_chunk) >= self.min_chunk_size:
                    chunks.append(self._create_chunk(
                        content=current_chunk,
                        document_id=document_id,
                        chunk_id=chunk_counter,
                        metadata=metadata,
                        start_index=current_start
                    ))
                    chunk_counter += 1

                # Handle overlap
                if self.chunk_overlap > 0 and current_chunk:
                    overlap_text = self._get_overlap_text(current_chunk)
                    current_chunk = f"{overlap_text} {sentence}".strip()
                else:
                    current_chunk = sentence

                current_start = len(content) - len(current_chunk)

        # Add final chunk
        if current_chunk and count_tokens(current_chunk) >= self.min_chunk_size:
            chunks.append(self._create_chunk(
                content=current_chunk,
                document_id=document_id,
                chunk_id=chunk_counter,
                metadata=metadata,
                start_index=current_start
            ))

        logger.info(f"Created {len(chunks)} chunks from document {document_id}")
        return chunks

    def _get_overlap_text(self, text: str) -> str:
        """Get the last portion of text for overlap."""
        tokens = text.split()
        if len(tokens) <= self.chunk_overlap:
            return text
        return " ".join(tokens[-self.chunk_overlap:])

    def _create_chunk(
        self,
        content: str,
        document_id: str,
        chunk_id: int,
        metadata: Dict[str, Any],
        start_index: int
    ) -> DocumentChunk:
        """Create a document chunk with proper metadata."""
        chunk_metadata = {
            **metadata,
            "chunk_id": chunk_id,
            "chunk_type": "sentence_boundary",
            "parent_document": document_id,
            "token_count": count_tokens(content)
        }

        return DocumentChunk(
            id=f"{document_id}#chunk_{chunk_id}",
            content=content.strip(),
            metadata=chunk_metadata,
            start_index=start_index,
            end_index=start_index + len(content)
        )


class DestinationGuideChunker(DocumentChunker):
    """Chunker for destination guides that preserves section context."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Patterns for common travel guide sections
        self.section_patterns = [
            re.compile(r'^#{1,3}\s+(.+)$', re.MULTILINE),  # Markdown headers
            re.compile(r'^([A-Z][A-Z\s]+)$', re.MULTILINE),  # ALL CAPS headers
            re.compile(r'^\*\*([^*]+)\*\*', re.MULTILINE),   # Bold section headers
            re.compile(r'^(Overview|Getting There|Where to Stay|What to See|Activities|Food|Transportation|Tips):', re.MULTILINE | re.IGNORECASE)
        ]

    def chunk_document(
        self,
        content: str,
        document_id: str,
        metadata: Dict[str, Any]
    ) -> List[DocumentChunk]:
        """Chunk destination guides by sections."""
        sections = self._split_into_sections(content)
        chunks = []
        chunk_counter = 0

        for section_title, section_content in sections:
            if not section_content.strip():
                continue

            section_metadata = {
                **metadata,
                "section_title": section_title,
                "document_type": "destination_guide"
            }

            # If section is small enough, keep as one chunk
            if count_tokens(section_content) <= self.chunk_size:
                chunks.append(self._create_section_chunk(
                    content=section_content,
                    document_id=document_id,
                    chunk_id=chunk_counter,
                    section_title=section_title,
                    metadata=section_metadata
                ))
                chunk_counter += 1
            else:
                # Split large sections using sentence boundary chunker
                sentence_chunker = SentenceBoundaryChunker(
                    chunk_size=self.chunk_size,
                    chunk_overlap=self.chunk_overlap,
                    min_chunk_size=self.min_chunk_size
                )
                section_chunks = sentence_chunker.chunk_document(
                    section_content, document_id, section_metadata
                )

                # Update chunk IDs and add section context
                for chunk in section_chunks:
                    chunk.id = f"{document_id}#section_{section_title}#chunk_{chunk_counter}"
                    chunk.metadata["section_title"] = section_title
                    chunks.append(chunk)
                    chunk_counter += 1

        logger.info(f"Created {len(chunks)} section-based chunks from {document_id}")
        return chunks

    def _split_into_sections(self, content: str) -> List[tuple[str, str]]:
        """Split content into sections based on headers."""
        sections = []
        current_section = ("Introduction", "")
        current_content = []

        lines = content.split('\n')

        for line in lines:
            # Check if line matches any section pattern
            section_title = self._extract_section_title(line)

            if section_title:
                # Save previous section
                if current_content or current_section[1]:
                    sections.append((
                        current_section[0],
                        current_section[1] + '\n'.join(current_content)
                    ))

                # Start new section
                current_section = (section_title, "")
                current_content = []
            else:
                current_content.append(line)

        # Add final section
        if current_content or current_section[1]:
            sections.append((
                current_section[0],
                current_section[1] + '\n'.join(current_content)
            ))

        return sections

    def _extract_section_title(self, line: str) -> Optional[str]:
        """Extract section title from a line if it matches header patterns."""
        for pattern in self.section_patterns:
            match = pattern.match(line.strip())
            if match:
                return match.group(1).strip()
        return None

    def _create_section_chunk(
        self,
        content: str,
        document_id: str,
        chunk_id: int,
        section_title: str,
        metadata: Dict[str, Any]
    ) -> DocumentChunk:
        """Create a section-based chunk."""
        chunk_metadata = {
            **metadata,
            "chunk_id": chunk_id,
            "chunk_type": "section",
            "section_title": section_title,
            "parent_document": document_id,
            "token_count": count_tokens(content)
        }

        return DocumentChunk(
            id=f"{document_id}#section_{section_title}#chunk_{chunk_id}",
            content=content.strip(),
            metadata=chunk_metadata
        )


class HotelListingChunker(DocumentChunker):
    """Chunker for hotel listings that keeps hotel information together."""

    def chunk_document(
        self,
        content: str,
        document_id: str,
        metadata: Dict[str, Any]
    ) -> List[DocumentChunk]:
        """Chunk hotel listings by individual hotels."""
        hotels = self._extract_hotels(content)
        chunks = []

        for i, hotel_info in enumerate(hotels):
            hotel_metadata = {
                **metadata,
                "document_type": "hotel_listing",
                "hotel_name": hotel_info.get("name", f"Hotel_{i}"),
                "hotel_category": hotel_info.get("category", "unknown")
            }

            chunks.append(DocumentChunk(
                id=f"{document_id}#hotel_{i}",
                content=hotel_info["content"],
                metadata={
                    **hotel_metadata,
                    "chunk_id": i,
                    "chunk_type": "hotel",
                    "parent_document": document_id,
                    "token_count": count_tokens(hotel_info["content"])
                }
            ))

        logger.info(f"Created {len(chunks)} hotel chunks from {document_id}")
        return chunks

    def _extract_hotels(self, content: str) -> List[Dict[str, Any]]:
        """Extract individual hotel information from content."""
        # Patterns for hotel section identification
        hotel_patterns = [
            re.compile(r'^(\d+\.\s*)?([^:\n]+)(?:\s*:\s*|\n)', re.MULTILINE),  # "1. Hotel Name:" or "Hotel Name\n"
            re.compile(r'\*\*([^*]+)\*\*', re.MULTILINE),  # **Hotel Name**
            re.compile(r'^([A-Z][^.\n]*(?:Hotel|Resort|Inn|Lodge|Hostel)[^.\n]*)$', re.MULTILINE)  # Hotel name patterns
        ]

        hotels = []
        sections = re.split(r'\n(?=\d+\.\s|\*\*[^*]+\*\*)', content)

        for section in sections:
            section = section.strip()
            if not section:
                continue

            # Extract hotel name
            hotel_name = self._extract_hotel_name(section)
            hotel_category = self._guess_hotel_category(section)

            hotels.append({
                "name": hotel_name,
                "category": hotel_category,
                "content": section
            })

        return hotels if hotels else [{"name": "Unknown", "category": "unknown", "content": content}]

    def _extract_hotel_name(self, section: str) -> str:
        """Extract hotel name from a section."""
        lines = section.split('\n')
        first_line = lines[0].strip()

        # Remove numbering and formatting
        name = re.sub(r'^\d+\.\s*', '', first_line)
        name = re.sub(r'^\*\*([^*]+)\*\*.*', r'\1', name)
        name = re.sub(r'^([^:]+):.*', r'\1', name)

        return name.strip() or "Unknown Hotel"

    def _guess_hotel_category(self, content: str) -> str:
        """Guess hotel category from content."""
        content_lower = content.lower()

        if any(word in content_lower for word in ["luxury", "5-star", "premium", "suite"]):
            return "luxury"
        elif any(word in content_lower for word in ["budget", "hostel", "cheap", "affordable"]):
            return "budget"
        elif any(word in content_lower for word in ["boutique", "4-star", "mid-range"]):
            return "mid-range"
        else:
            return "unknown"


class PolicyDocumentChunker(DocumentChunker):
    """Chunker for policy documents (visa rules, airline policies) that preserves legal accuracy."""

    def chunk_document(
        self,
        content: str,
        document_id: str,
        metadata: Dict[str, Any]
    ) -> List[DocumentChunk]:
        """Chunk policy documents by maintaining policy integrity."""
        policies = self._split_policies(content)
        chunks = []

        for i, (policy_title, policy_content) in enumerate(policies):
            if not policy_content.strip():
                continue

            policy_metadata = {
                **metadata,
                "document_type": "policy",
                "policy_title": policy_title,
                "policy_type": self._classify_policy(policy_content)
            }

            # Keep policies intact if possible
            if count_tokens(policy_content) <= self.chunk_size:
                chunks.append(DocumentChunk(
                    id=f"{document_id}#policy_{i}",
                    content=policy_content.strip(),
                    metadata={
                        **policy_metadata,
                        "chunk_id": i,
                        "chunk_type": "policy",
                        "parent_document": document_id,
                        "token_count": count_tokens(policy_content)
                    }
                ))
            else:
                # Split large policies carefully
                sub_chunks = self._split_large_policy(
                    policy_content, document_id, i, policy_metadata
                )
                chunks.extend(sub_chunks)

        logger.info(f"Created {len(chunks)} policy chunks from {document_id}")
        return chunks

    def _split_policies(self, content: str) -> List[tuple[str, str]]:
        """Split content into individual policies."""
        # Common policy section patterns
        section_patterns = [
            re.compile(r'^(\d+\.\d*\s*[^.\n]+)$', re.MULTILINE),  # "1.1 Policy Name"
            re.compile(r'^([A-Z][^:\n]*(?:Policy|Rule|Requirement|Regulation)[^:\n]*):', re.MULTILINE),
            re.compile(r'^#{1,3}\s+(.+)$', re.MULTILINE),  # Markdown headers
        ]

        policies = []
        current_title = "General Policy"
        current_content = []

        lines = content.split('\n')

        for line in lines:
            # Check if line is a policy header
            policy_title = None
            for pattern in section_patterns:
                match = pattern.match(line.strip())
                if match:
                    policy_title = match.group(1).strip()
                    break

            if policy_title:
                # Save previous policy
                if current_content:
                    policies.append((current_title, '\n'.join(current_content)))

                # Start new policy
                current_title = policy_title
                current_content = []
            else:
                current_content.append(line)

        # Add final policy
        if current_content:
            policies.append((current_title, '\n'.join(current_content)))

        return policies

    def _classify_policy(self, content: str) -> str:
        """Classify policy type based on content."""
        content_lower = content.lower()

        if any(word in content_lower for word in ["visa", "entry", "passport", "border"]):
            return "visa_policy"
        elif any(word in content_lower for word in ["baggage", "airline", "flight", "cancellation"]):
            return "airline_policy"
        elif any(word in content_lower for word in ["hotel", "accommodation", "booking", "reservation"]):
            return "hotel_policy"
        else:
            return "general_policy"

    def _split_large_policy(
        self,
        content: str,
        document_id: str,
        policy_index: int,
        metadata: Dict[str, Any]
    ) -> List[DocumentChunk]:
        """Split large policy while maintaining context."""
        # Use sentence chunker but with larger overlap for policy context
        chunker = SentenceBoundaryChunker(
            chunk_size=self.chunk_size,
            chunk_overlap=max(self.chunk_overlap, 100),  # Larger overlap for policies
            min_chunk_size=self.min_chunk_size
        )

        chunks = chunker.chunk_document(content, f"{document_id}#policy_{policy_index}", metadata)

        # Update chunk IDs and add policy context
        for i, chunk in enumerate(chunks):
            chunk.id = f"{document_id}#policy_{policy_index}#subchunk_{i}"
            chunk.metadata.update({
                "chunk_type": "policy_subchunk",
                "parent_policy": policy_index
            })

        return chunks


def create_chunker(
    document_type: str = "general",
    **kwargs
) -> DocumentChunker:
    """Factory function to create appropriate chunker based on document type."""
    chunker_map = {
        "destination": DestinationGuideChunker,
        "destination_guide": DestinationGuideChunker,
        "hotel": HotelListingChunker,
        "hotel_listing": HotelListingChunker,
        "policy": PolicyDocumentChunker,
        "visa": PolicyDocumentChunker,
        "airline": PolicyDocumentChunker,
        "general": SentenceBoundaryChunker
    }

    chunker_class = chunker_map.get(document_type, SentenceBoundaryChunker)
    return chunker_class(**kwargs)