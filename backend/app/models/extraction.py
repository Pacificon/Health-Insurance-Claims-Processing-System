from pydantic import BaseModel, Field


class LineItem(BaseModel):
    description: str
    amount: float = Field(ge=0)


class ExtractedClaim(BaseModel):
    """Structured claim data after document extraction."""

    diagnosis: str | None = None
    treatment: str | None = None
    tests_ordered: list[str] = Field(default_factory=list)
    line_items: list[LineItem] = Field(default_factory=list)
    hospital_name: str | None = None
    pre_authorization_obtained: bool = False

    @classmethod
    def from_document_contents(cls, documents: list) -> "ExtractedClaim":
        """Merge embedded document content dicts (eval mode) into one extracted claim."""
        diagnosis: str | None = None
        treatment: str | None = None
        tests_ordered: list[str] = []
        line_items: list[LineItem] = []
        hospital_name: str | None = None

        for doc in documents:
            content = getattr(doc, "content", None) or (doc.get("content") if isinstance(doc, dict) else None)
            if not content:
                continue
            diagnosis = diagnosis or content.get("diagnosis")
            treatment = treatment or content.get("treatment")
            hospital_name = hospital_name or content.get("hospital_name")
            if content.get("tests_ordered"):
                tests_ordered.extend(content["tests_ordered"])
            if content.get("test_name"):
                tests_ordered.append(content["test_name"])
            for item in content.get("line_items", []):
                line_items.append(LineItem(description=item["description"], amount=float(item["amount"])))

        return cls(
            diagnosis=diagnosis,
            treatment=treatment,
            tests_ordered=tests_ordered,
            line_items=line_items,
            hospital_name=hospital_name,
        )
