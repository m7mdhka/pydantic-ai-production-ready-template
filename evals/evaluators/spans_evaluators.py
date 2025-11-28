"""Spans evaluators."""

from dataclasses import dataclass

from pydantic_evals.evaluators import Evaluator, EvaluatorContext
from pydantic_evals.otel import SpanQuery, SpanTree


@dataclass
class OnlySpecificSpan(Evaluator):
    """Evaluator that checks if only the specific span is present in the span tree."""

    specific_query: SpanQuery
    evaluation_name: str

    def evaluate(self, ctx: EvaluatorContext) -> dict[str, bool]:
        """Evaluate the specific span."""
        span_tree: SpanTree = ctx.span_tree

        specific_spans = span_tree.find(lambda node: node.matches(self.specific_query))
        if len(specific_spans) == 0:
            return {self.evaluation_name: False}

        all_spans = list(span_tree)
        tool_spans = [
            span
            for span in all_spans
            if getattr(span, "attributes", {}).get("gen_ai.tool.name")
        ]

        passes = len(tool_spans) > 0 and all(
            span.matches(self.specific_query) for span in tool_spans
        )
        return {self.evaluation_name: passes}


@dataclass
class NoSpanShouldBeCalled(Evaluator):
    """Evaluator that checks if no spans matching the query are present."""

    query: SpanQuery | None = None
    evaluation_name: str = "no_spans_called"

    def evaluate(self, ctx: EvaluatorContext) -> dict[str, bool]:
        """Evaluate the no span should be called."""
        span_tree: SpanTree = ctx.span_tree

        if self.query is not None:
            query = self.query
            matching_spans = span_tree.find(lambda node: node.matches(query))
            passes = len(matching_spans) == 0
        else:
            all_spans = list(span_tree)
            tool_spans = [
                span
                for span in all_spans
                if getattr(span, "attributes", {}).get("gen_ai.tool.name")
            ]
            passes = len(tool_spans) == 0

        return {self.evaluation_name: passes}
