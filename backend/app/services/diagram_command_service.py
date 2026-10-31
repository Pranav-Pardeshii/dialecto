import json
import re
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

CONTENT_DIR = Path(__file__).parent.parent / "content"


class VoiceCommandResult(BaseModel):
    action: str
    target_structure_id: str | None = None
    target_structure_name: str | None = None
    pathway_id: str | None = None
    view_direction: str | None = None
    zoom_level: float | None = None
    message: str
    clarification_options: list[str] = Field(default_factory=list)
    confidence: float = 1.0


class DiagramCommandService:
    def __init__(self) -> None:
        manifest_file = CONTENT_DIR / "diagram_manifest.json"
        with open(manifest_file, encoding="utf-8") as f:
            data = json.load(f)
        self.manifests: dict[str, dict[str, Any]] = {d["id"]: d for d in data.get("diagrams", [])}

    def get_manifest(self, diagram_id: str) -> dict[str, Any] | None:
        return self.manifests.get(diagram_id)

    def list_diagrams(self) -> list[dict[str, Any]]:
        return list(self.manifests.values())

    def interpret_command(
        self,
        diagram_id: str,
        spoken_text: str,
        is_assessment_mode: bool = False,
        target_question_id: str | None = None,
    ) -> VoiceCommandResult:
        manifest = self.get_manifest(diagram_id)
        if not manifest:
            return VoiceCommandResult(
                action="UNKNOWN",
                message=f"Diagram '{diagram_id}' is not loaded.",
                confidence=0.0,
            )

        raw = spoken_text.strip()
        lower = raw.lower()

        # 1. Security & Prompt Injection Prevention
        injection_patterns = [
            r"ignore previous",
            r"set mastery",
            r"give me full",
            r"system prompt",
            r"drop table",
            r"delete from",
            r"bypass",
        ]
        if any(re.search(pat, lower) for pat in injection_patterns):
            return VoiceCommandResult(
                action="REJECTED_UNAUTHORIZED",
                message="Command rejected: Spoken input contains unauthorized system instructions.",
                confidence=1.0,
            )

        # 2. Assessment Mode Safety Guard
        if is_assessment_mode:
            # In active assessment, commands attempting to reveal the answer are blocked or routed to submission
            reveal_verbs = ["show", "highlight", "where is", "point to", "find"]
            if any(re.search(rf"\b{verb}\b", lower) for verb in reveal_verbs) and not any(
                ans_word in lower for ans_word in ["answer is", "i think", "my answer", "this is"]
            ):
                return VoiceCommandResult(
                    action="ASSESSMENT_SAFETY_BLOCKED",
                    message="Structure visualization is locked during an active assessment. Submit your answer or identify the structure directly.",
                    confidence=1.0,
                )

        # 3. Global Diagram Controls (Reset, Rotate, Zoom)
        if re.search(r"\b(reset|re-center|recenter|default view|restore|restart view)\b", lower):
            return VoiceCommandResult(
                action="RESET_VIEW",
                message="Resetting camera and restoring all structure visibilities.",
                confidence=1.0,
            )

        if re.search(r"\b(rotate|turn around|spin|orbit|tilt)\b", lower):
            direction = "right"
            if "left" in lower:
                direction = "left"
            elif "up" in lower or "top" in lower:
                direction = "up"
            elif "down" in lower:
                direction = "down"
            return VoiceCommandResult(
                action="ROTATE_VIEW",
                view_direction=direction,
                message=f"Rotating diagram view {direction}.",
                confidence=0.95,
            )

        if re.search(r"\b(zoom in|magnify|closer)\b", lower):
            return VoiceCommandResult(
                action="ZOOM_VIEW",
                zoom_level=1.5,
                message="Zooming in on the biological model.",
                confidence=0.95,
            )

        if re.search(r"\b(zoom out|step back|wider)\b", lower):
            return VoiceCommandResult(
                action="ZOOM_VIEW",
                zoom_level=0.7,
                message="Zooming out to full organ perspective.",
                confidence=0.95,
            )

        # 4. Pathway Tracing
        if re.search(r"\b(trace|blood flow|filtrate|pathway|circulation|flow|cycle)\b", lower):
            pathways = manifest.get("pathways", [])
            target_pathway = pathways[0]["id"] if pathways else None
            p_name = pathways[0]["name"] if pathways else "Pathway"
            if "pulmonary" in lower and len(pathways) > 0:
                target_pathway = pathways[0]["id"]
                p_name = pathways[0]["name"]
            elif "systemic" in lower and len(pathways) > 1:
                target_pathway = pathways[1]["id"]
                p_name = pathways[1]["name"]

            return VoiceCommandResult(
                action="TRACE_PATHWAY",
                pathway_id=target_pathway,
                message=f"Tracing biological pathway: {p_name}.",
                confidence=0.95,
            )

        # 5. Assessment Launch Controls
        if re.search(r"\b(quiz me|start assessment|test me|start quiz|begin test|exam)\b", lower):
            return VoiceCommandResult(
                action="START_ASSESSMENT",
                message=f"Starting interactive assessment for {manifest['display_name']}.",
                confidence=1.0,
            )

        # 6. Ask Pip or Verbal Explanation
        if re.search(r"\b(what is the function|how does|why is|explain to me|ask pip|tell me about)\b", lower):
            return VoiceCommandResult(
                action="ASK_PIP",
                message="Forwarding scientific query to Pip for contextual explanation.",
                confidence=0.90,
            )

        # 7. Ambiguity Resolution (e.g. "show the organelle" or "show the branch")
        if re.search(r"\b(organelle|organelles|structure|structures)\b", lower) and not any(
            w in lower for w in ["mitochondria", "mitochondrion", "nucleus", "chloroplast", "vacuole", "golgi", "lysosome", "microvilli", "myofibril"]
        ):
            if diagram_id == "plant":
                return VoiceCommandResult(
                    action="CLARIFY",
                    message="Plant cells contain several distinct organelles. Which one would you like to inspect?",
                    clarification_options=["Cell Wall", "Chloroplast", "Central Vacuole", "Nucleus"],
                    confidence=0.85,
                )
            if diagram_id == "whiteBlood":
                return VoiceCommandResult(
                    action="CLARIFY",
                    message="White blood cells contain specialized defense structures. Which one would you like to inspect?",
                    clarification_options=["Lobed Nucleus", "Lysosome", "Antimicrobial Granules"],
                    confidence=0.85,
                )
            if diagram_id == "epithelial":
                return VoiceCommandResult(
                    action="CLARIFY",
                    message="Epithelial cells contain specialized barrier and absorption structures. Which one would you like to inspect?",
                    clarification_options=["Microvilli", "Tight Junctions", "Nucleus"],
                    confidence=0.85,
                )
            if diagram_id == "muscle":
                return VoiceCommandResult(
                    action="CLARIFY",
                    message="Muscle fibers contain specialized contractile structures. Which one would you like to inspect?",
                    clarification_options=["Myofibril", "Sarcolemma", "Mitochondria"],
                    confidence=0.85,
                )
            return VoiceCommandResult(
                action="CLARIFY",
                message="The cell contains several specialized organelles. Which one would you like to inspect?",
                clarification_options=["Mitochondrion", "Nucleus", "Golgi Apparatus"],
                confidence=0.85,
            )

        if diagram_id == "neuron":
            if re.search(r"\b(branch|process|fiber)\b", lower) and not re.search(r"\b(dendrite|axon|soma)\b", lower):
                return VoiceCommandResult(
                    action="CLARIFY",
                    message="Neurons have two primary types of cellular processes. Which one would you like to inspect?",
                    clarification_options=["Dendrites", "Axon"],
                    confidence=0.85,
                )

        # 8. Structure Matching across Aliases
        structures = manifest.get("structures", [])
        matched_structure: dict[str, Any] | None = None

        # Check exact and substring aliases
        for s in structures:
            for alias in s["aliases"]:
                # Match whole words for short aliases like 'ra', 'rv', 'la', 'lv', 'pct', 'dct'
                if len(alias) <= 3:
                    if re.search(rf"\b{alias}\b", lower):
                        matched_structure = s
                        break
                elif alias in lower:
                    matched_structure = s
                    break
            if matched_structure:
                break

        if matched_structure:
            s_id = matched_structure["id"]
            s_name = matched_structure["name"]

            if is_assessment_mode:
                return VoiceCommandResult(
                    action="IDENTIFY_STRUCTURE",
                    target_structure_id=s_id,
                    target_structure_name=s_name,
                    message=f"Identified structure: {s_name}.",
                    confidence=0.98,
                )

            # Exploration mode actions
            if re.search(r"\b(hide|remove|conceal)\b", lower):
                return VoiceCommandResult(
                    action="HIDE_STRUCTURE",
                    target_structure_id=s_id,
                    target_structure_name=s_name,
                    message=f"Hiding {s_name} from view.",
                    confidence=0.95,
                )
            elif re.search(r"\b(isolate|only show|show only|focus on)\b", lower):
                return VoiceCommandResult(
                    action="ISOLATE_STRUCTURE",
                    target_structure_id=s_id,
                    target_structure_name=s_name,
                    message=f"Isolating {s_name}; other structures dimmed.",
                    confidence=0.95,
                )
            else:
                return VoiceCommandResult(
                    action="HIGHLIGHT_STRUCTURE",
                    target_structure_id=s_id,
                    target_structure_name=s_name,
                    message=f"Highlighting {s_name}: {matched_structure['description']}",
                    confidence=0.98,
                )

        # 9. Free-text scientific explanation submission
        if len(raw) > 20:
            return VoiceCommandResult(
                action="SUBMIT_EXPLANATION",
                message="Dictated scientific explanation received.",
                confidence=0.80,
            )

        # 10. Unknown / unmapped terminology
        return VoiceCommandResult(
            action="UNKNOWN",
            message=f"I couldn't identify a known biological command or organelle in '{raw}'. Try 'Show the nucleus', 'Isolate mitochondrion', or 'Reset view'.",
            confidence=0.30,
        )


diagram_command_service = DiagramCommandService()

