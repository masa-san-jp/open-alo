"""Compiler package for turning ALO documents into canonical Graph IR."""

from .compiler import CompileError, compile_alo, graph_to_json

__all__ = ["CompileError", "compile_alo", "graph_to_json"]
