from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.db.models import (
    CheckORM,
    DocumentORM,
    DocumentSectionORM,
    IssueORM,
    ProcessingSessionORM,
    RagIndexORM,
    RagSourceORM,
    RecommendationORM,
    ReportORM,
    UserORM,
)


class BackupService:
    """
    Сервис резервного копирования и восстановления.

    Backup v2.0 сохраняет нормализованную ER-схему:
    documents, document_sections, processing_sessions,
    reports, checks, issues, recommendations, rag_sources, rag_indexes.
    """

    def __init__(self, db: Session) -> None:
        self.db = db

    def create_backup_payload(self) -> dict[str, Any]:
        documents = self.db.query(DocumentORM).all()
        sections = self.db.query(DocumentSectionORM).all()
        sessions = self.db.query(ProcessingSessionORM).all()
        reports = self.db.query(ReportORM).all()
        checks = self.db.query(CheckORM).all()
        issues = self.db.query(IssueORM).all()
        recommendations = self.db.query(RecommendationORM).all()
        rag_sources = self.db.query(RagSourceORM).all()
        rag_indexes = self.db.query(RagIndexORM).all()

        return {
            "backup_version": "2.0",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "documents": [
                {
                    "id": document.id,
                    "owner_user_id": document.owner_user_id,
                    "filename": document.filename,
                    "document_type": document.document_type,
                    "source_format": document.source_format,
                    "processing_status": document.processing_status,
                    "storage_mode": document.storage_mode,
                    "created_at": self._datetime_to_iso(document.created_at),
                }
                for document in documents
            ],
            "document_sections": [
                {
                    "id": section.id,
                    "document_id": section.document_id,
                    "section_type": section.section_type,
                    "title": section.title,
                    "text": section.text,
                    "position_in_document": section.position_in_document,
                    "section_metadata": section.section_metadata,
                }
                for section in sections
            ],
            "processing_sessions": [
                {
                    "id": session.id,
                    "document_id": session.document_id,
                    "owner_user_id": session.owner_user_id,
                    "status": session.status,
                    "started_at": self._datetime_to_iso(session.started_at),
                    "ended_at": self._datetime_to_iso(session.ended_at),
                    "duration_ms": session.duration_ms,
                    "session_metadata": session.session_metadata,
                }
                for session in sessions
            ],
            "reports": [
                {
                    "id": report.id,
                    "owner_user_id": report.owner_user_id,
                    "document_id": report.document_id,
                    "processing_session_id": report.processing_session_id,
                    "filename": report.filename,
                    "summary_status": report.summary_status,
                    "total_issues": report.total_issues,
                    "critical_count": report.critical_count,
                    "major_count": report.major_count,
                    "minor_count": report.minor_count,
                    "summary": report.summary,
                    "report_json": report.report_json,
                    "created_at": self._datetime_to_iso(report.created_at),
                }
                for report in reports
            ],
            "checks": [
                {
                    "id": check.id,
                    "processing_session_id": check.processing_session_id,
                    "document_id": check.document_id,
                    "report_id": check.report_id,
                    "agent_name": check.agent_name,
                    "check_type": check.check_type,
                    "status": check.status,
                    "started_at": self._datetime_to_iso(check.started_at),
                    "ended_at": self._datetime_to_iso(check.ended_at),
                    "duration_ms": check.duration_ms,
                    "model_or_ruleset_version": check.model_or_ruleset_version,
                    "error_message": check.error_message,
                }
                for check in checks
            ],
            "issues": [
                {
                    "id": issue.id,
                    "check_id": issue.check_id,
                    "document_id": issue.document_id,
                    "report_id": issue.report_id,
                    "severity": issue.severity,
                    "issue_type": issue.issue_type,
                    "description": issue.description,
                    "evidence_fragment": issue.evidence_fragment,
                    "source_agent": issue.source_agent,
                    "confidence_score": issue.confidence_score,
                    "issue_metadata": issue.issue_metadata,
                }
                for issue in issues
            ],
            "recommendations": [
                {
                    "id": recommendation.id,
                    "issue_id": recommendation.issue_id,
                    "recommendation_text": recommendation.recommendation_text,
                    "example_fix": recommendation.example_fix,
                    "priority_order": recommendation.priority_order,
                }
                for recommendation in recommendations
            ],
            "rag_sources": [
                {
                    "id": source.id,
                    "owner_user_id": source.owner_user_id,
                    "title": source.title,
                    "filename": source.filename,
                    "source_type": source.source_type,
                    "source_format": source.source_format,
                    "content": source.content,
                    "content_hash": source.content_hash,
                    "file_size_bytes": source.file_size_bytes,
                    "is_active": source.is_active,
                    "source_metadata": source.source_metadata,
                    "created_at": self._datetime_to_iso(source.created_at),
                    "updated_at": self._datetime_to_iso(source.updated_at),
                }
                for source in rag_sources
            ],
            "rag_indexes": [
                {
                    "id": rag_index.id,
                    "owner_user_id": rag_index.owner_user_id,
                    "status": rag_index.status,
                    "reindex_required": rag_index.reindex_required,
                    "index_path": rag_index.index_path,
                    "chunks_path": rag_index.chunks_path,
                    "sources_hash": rag_index.sources_hash,
                    "sources_count": rag_index.sources_count,
                    "chunks_count": rag_index.chunks_count,
                    "embedding_backend": rag_index.embedding_backend,
                    "embedding_model_name": rag_index.embedding_model_name,
                    "embedding_dimension": rag_index.embedding_dimension,
                    "retriever_type": rag_index.retriever_type,
                    "index_metadata": rag_index.index_metadata or {},
                    "error_message": rag_index.error_message,
                    "last_reindexed_at": self._datetime_to_iso(
                        rag_index.last_reindexed_at
                    ),
                    "created_at": self._datetime_to_iso(rag_index.created_at),
                    "updated_at": self._datetime_to_iso(rag_index.updated_at),
                }
                for rag_index in rag_indexes
            ],
        }

    def restore_from_payload(self, payload: dict[str, Any]) -> dict[str, int]:
        """
        Восстанавливает данные из backup payload.

        Порядок восстановления соответствует внешним ключам:
        documents -> document_sections -> processing_sessions -> reports
        -> checks -> issues -> recommendations -> rag_sources -> rag_indexes.
        """

        restored_documents = self._restore_documents(payload)
        self.db.flush()

        restored_document_sections = self._restore_document_sections(payload)
        self.db.flush()

        restored_processing_sessions = self._restore_processing_sessions(payload)
        self.db.flush()

        restored_reports = self._restore_reports(payload)
        self.db.flush()

        restored_checks = self._restore_checks(payload)
        self.db.flush()

        restored_issues = self._restore_issues(payload)
        self.db.flush()

        restored_recommendations = self._restore_recommendations(payload)
        self.db.flush()

        restored_rag_sources = self._restore_rag_sources(payload)
        self.db.flush()

        restored_rag_indexes = self._restore_rag_indexes(payload)

        self.db.commit()

        return {
            "restored_documents": restored_documents,
            "restored_document_sections": restored_document_sections,
            "restored_processing_sessions": restored_processing_sessions,
            "restored_reports": restored_reports,
            "restored_checks": restored_checks,
            "restored_issues": restored_issues,
            "restored_recommendations": restored_recommendations,
            "restored_rag_sources": restored_rag_sources,
            "restored_rag_indexes": restored_rag_indexes,
        }

    def _restore_documents(self, payload: dict[str, Any]) -> int:
        restored = 0

        for document_data in payload.get("documents", []):
            document_id = document_data["id"]

            if self.db.get(DocumentORM, document_id) is not None:
                continue

            document = DocumentORM(
                id=document_id,
                owner_user_id=document_data.get("owner_user_id"),
                filename=document_data["filename"],
                document_type=document_data["document_type"],
                source_format=document_data["source_format"],
                processing_status=document_data["processing_status"],
                storage_mode=document_data["storage_mode"],
                created_at=self._parse_datetime_or_now(
                    document_data.get("created_at")
                ),
            )

            self.db.add(document)
            restored += 1

        return restored

    def _restore_document_sections(self, payload: dict[str, Any]) -> int:
        restored = 0

        for section_data in payload.get("document_sections", []):
            section_id = section_data["id"]

            if self.db.get(DocumentSectionORM, section_id) is not None:
                continue

            section = DocumentSectionORM(
                id=section_id,
                document_id=section_data["document_id"],
                section_type=section_data["section_type"],
                title=section_data.get("title"),
                text=section_data["text"],
                position_in_document=section_data["position_in_document"],
                section_metadata=section_data.get("section_metadata") or {},
            )

            self.db.add(section)
            restored += 1

        return restored

    def _restore_processing_sessions(self, payload: dict[str, Any]) -> int:
        restored = 0

        for session_data in payload.get("processing_sessions", []):
            session_id = session_data["id"]

            if self.db.get(ProcessingSessionORM, session_id) is not None:
                continue

            processing_session = ProcessingSessionORM(
                id=session_id,
                document_id=session_data["document_id"],
                owner_user_id=session_data.get("owner_user_id"),
                status=session_data.get("status", "completed"),
                started_at=self._parse_datetime_or_now(
                    session_data.get("started_at")
                ),
                ended_at=self._parse_datetime(session_data.get("ended_at")),
                duration_ms=session_data.get("duration_ms"),
                session_metadata=session_data.get("session_metadata") or {},
            )

            self.db.add(processing_session)
            restored += 1

        return restored

    def _restore_reports(self, payload: dict[str, Any]) -> int:
        restored = 0

        for report_data in payload.get("reports", []):
            report_id = report_data["id"]

            if self.db.get(ReportORM, report_id) is not None:
                continue

            report = ReportORM(
                id=report_id,
                owner_user_id=report_data.get("owner_user_id"),
                document_id=report_data["document_id"],
                processing_session_id=report_data.get("processing_session_id"),
                filename=report_data["filename"],
                summary_status=report_data["summary_status"],
                total_issues=report_data["total_issues"],
                critical_count=report_data["critical_count"],
                major_count=report_data["major_count"],
                minor_count=report_data["minor_count"],
                summary=report_data["summary"],
                report_json=report_data["report_json"],
                created_at=self._parse_datetime_or_now(
                    report_data.get("created_at")
                ),
            )

            self.db.add(report)
            restored += 1

        return restored

    def _restore_checks(self, payload: dict[str, Any]) -> int:
        restored = 0

        for check_data in payload.get("checks", []):
            check_id = check_data["id"]

            if self.db.get(CheckORM, check_id) is not None:
                continue

            check = CheckORM(
                id=check_id,
                processing_session_id=check_data["processing_session_id"],
                document_id=check_data["document_id"],
                report_id=check_data.get("report_id"),
                agent_name=check_data["agent_name"],
                check_type=check_data["check_type"],
                status=check_data["status"],
                started_at=self._parse_datetime_or_now(
                    check_data.get("started_at")
                ),
                ended_at=self._parse_datetime_or_now(
                    check_data.get("ended_at")
                ),
                duration_ms=check_data.get("duration_ms", 0.0),
                model_or_ruleset_version=check_data.get(
                    "model_or_ruleset_version",
                    "ruleset-1.0.0",
                ),
                error_message=check_data.get("error_message"),
            )

            self.db.add(check)
            restored += 1

        return restored

    def _restore_issues(self, payload: dict[str, Any]) -> int:
        restored = 0

        for issue_data in payload.get("issues", []):
            issue_id = issue_data["id"]

            if self.db.get(IssueORM, issue_id) is not None:
                continue

            issue = IssueORM(
                id=issue_id,
                check_id=issue_data["check_id"],
                document_id=issue_data["document_id"],
                report_id=issue_data["report_id"],
                severity=issue_data["severity"],
                issue_type=issue_data["issue_type"],
                description=issue_data["description"],
                evidence_fragment=issue_data.get("evidence_fragment"),
                source_agent=issue_data["source_agent"],
                confidence_score=issue_data.get("confidence_score"),
                issue_metadata=issue_data.get("issue_metadata") or {},
            )

            self.db.add(issue)
            restored += 1

        return restored

    def _restore_recommendations(self, payload: dict[str, Any]) -> int:
        restored = 0

        for recommendation_data in payload.get("recommendations", []):
            recommendation_id = recommendation_data["id"]

            if self.db.get(RecommendationORM, recommendation_id) is not None:
                continue

            recommendation = RecommendationORM(
                id=recommendation_id,
                issue_id=recommendation_data["issue_id"],
                recommendation_text=recommendation_data["recommendation_text"],
                example_fix=recommendation_data.get("example_fix"),
                priority_order=recommendation_data.get("priority_order", 0),
            )

            self.db.add(recommendation)
            restored += 1

        return restored

    def _restore_rag_sources(self, payload: dict[str, Any]) -> int:
        restored = 0

        for source_data in payload.get("rag_sources", []):
            source_id = source_data["id"]

            if self.db.get(RagSourceORM, source_id) is not None:
                continue

            owner_user_id = source_data.get("owner_user_id")

            if owner_user_id is not None and self.db.get(UserORM, owner_user_id) is None:
                owner_user_id = None

            rag_source = RagSourceORM(
                id=source_id,
                owner_user_id=owner_user_id,
                title=source_data["title"],
                filename=source_data["filename"],
                source_type=source_data.get("source_type", "other"),
                source_format=source_data["source_format"],
                content=source_data["content"],
                content_hash=source_data["content_hash"],
                file_size_bytes=source_data.get("file_size_bytes", 0),
                is_active=source_data.get("is_active", True),
                source_metadata=source_data.get("source_metadata") or {},
                created_at=self._parse_datetime_or_now(
                    source_data.get("created_at")
                ),
                updated_at=self._parse_datetime_or_now(
                    source_data.get("updated_at")
                ),
            )

            self.db.add(rag_source)
            restored += 1

        return restored

    def _restore_rag_indexes(self, payload: dict[str, Any]) -> int:
        """
        Восстанавливает метаданные персональных RAG-индексов.

        Бинарные faiss.index/chunks.json в backup не входят, поэтому после restore
        индекс принудительно помечается как stale и reindex_required=True.
        Это защищает систему от ситуации, когда БД считает индекс ready,
        но файлов индекса на диске нет.
        """

        restored = 0

        for index_data in payload.get("rag_indexes", []):
            index_id = index_data["id"]
            owner_user_id = index_data["owner_user_id"]

            if self.db.get(RagIndexORM, index_id) is not None:
                continue

            if self.db.get(UserORM, owner_user_id) is None:
                continue

            existing_owner_index = (
                self.db.query(RagIndexORM)
                .filter(RagIndexORM.owner_user_id == owner_user_id)
                .one_or_none()
            )

            if existing_owner_index is not None:
                continue

            rag_index = RagIndexORM(
                id=index_id,
                owner_user_id=owner_user_id,
                status="stale",
                reindex_required=True,
                index_path=index_data.get("index_path"),
                chunks_path=index_data.get("chunks_path"),
                sources_hash=index_data.get("sources_hash"),
                sources_count=index_data.get("sources_count", 0),
                chunks_count=index_data.get("chunks_count", 0),
                embedding_backend=index_data.get("embedding_backend", "hashing"),
                embedding_model_name=index_data.get(
                    "embedding_model_name",
                    "hashing",
                ),
                embedding_dimension=index_data.get("embedding_dimension", 384),
                retriever_type=index_data.get("retriever_type", "faiss"),
                index_metadata={
                    **(index_data.get("index_metadata") or {}),
                    "restored_from_backup": True,
                    "restore_note": (
                        "FAISS binary files are not included in backup; "
                        "run reindex before search."
                    ),
                },
                error_message=index_data.get("error_message"),
                last_reindexed_at=self._parse_datetime(
                    index_data.get("last_reindexed_at")
                ),
                created_at=self._parse_datetime_or_now(
                    index_data.get("created_at")
                ),
                updated_at=datetime.now(timezone.utc),
            )

            self.db.add(rag_index)
            restored += 1

        return restored

    @staticmethod
    def _datetime_to_iso(value: datetime | None) -> str | None:
        if value is None:
            return None

        return value.isoformat()

    @staticmethod
    def _parse_datetime(value: str | None) -> datetime | None:
        if not value:
            return None

        return datetime.fromisoformat(value)

    @classmethod
    def _parse_datetime_or_now(cls, value: str | None) -> datetime:
        parsed = cls._parse_datetime(value)

        if parsed is not None:
            return parsed

        return datetime.now(timezone.utc)