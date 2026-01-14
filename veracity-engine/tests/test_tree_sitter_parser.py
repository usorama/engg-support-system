"""
Tests for the tree-sitter multi-language AST parser.

STORY-020: Multi-language AST support
"""

import pytest
from core.tree_sitter_parser import (
    TreeSitterParser,
    parse_source_file,
    get_parser,
    TREE_SITTER_AVAILABLE,
    ParseResult,
)


# Skip all tests if tree-sitter is not available
pytestmark = pytest.mark.skipif(
    not TREE_SITTER_AVAILABLE,
    reason="tree-sitter not installed"
)


class TestTreeSitterParser:
    """Tests for TreeSitterParser class."""

    def test_parser_initialization(self):
        """Test that parser initializes with all supported languages."""
        parser = get_parser()
        assert parser.is_available()
        assert parser.supports_language('python')
        assert parser.supports_language('typescript')
        assert parser.supports_language('javascript')
        assert parser.supports_language('go')
        assert parser.supports_language('rust')
        assert parser.supports_language('java')

    def test_extension_mapping(self):
        """Test file extension to language mapping."""
        parser = get_parser()
        assert parser.get_language_for_extension('.py') == 'python'
        assert parser.get_language_for_extension('.ts') == 'typescript'
        assert parser.get_language_for_extension('.tsx') == 'tsx'
        assert parser.get_language_for_extension('.js') == 'javascript'
        assert parser.get_language_for_extension('.go') == 'go'
        assert parser.get_language_for_extension('.rs') == 'rust'
        assert parser.get_language_for_extension('.java') == 'java'
        assert parser.get_language_for_extension('.unknown') is None


class TestPythonParsing:
    """Tests for Python AST extraction."""

    def test_parse_python_function(self):
        """Test extracting Python functions."""
        code = '''
def hello_world():
    """Say hello."""
    print("Hello, World!")

async def async_func():
    await something()
'''
        result = parse_source_file(code, '.py')
        assert result.success
        assert result.language == 'python'
        assert len(result.functions) == 2

        hello = next(f for f in result.functions if f.name == 'hello_world')
        assert hello.qualified_name == 'hello_world'
        assert hello.is_async is False

        async_fn = next(f for f in result.functions if f.name == 'async_func')
        assert async_fn.is_async is True

    def test_parse_python_class(self):
        """Test extracting Python classes."""
        code = '''
class MyClass(BaseClass, Mixin):
    """A test class."""

    def method(self):
        pass
'''
        result = parse_source_file(code, '.py')
        assert result.success
        assert len(result.classes) == 1

        cls = result.classes[0]
        assert cls.name == 'MyClass'
        assert 'BaseClass' in cls.parent_classes

    def test_parse_python_imports(self):
        """Test extracting Python imports."""
        code = '''
import os
import sys
from typing import List, Dict
from collections import defaultdict as dd
'''
        result = parse_source_file(code, '.py')
        assert result.success
        assert len(result.imports) >= 2


class TestTypeScriptParsing:
    """Tests for TypeScript/JavaScript AST extraction."""

    def test_parse_typescript_function(self):
        """Test extracting TypeScript functions."""
        code = '''
function greet(name: string): void {
    console.log(`Hello, ${name}!`);
}

export async function fetchData(): Promise<void> {
    await fetch('/api');
}

const arrowFunc = () => {
    return 42;
};
'''
        result = parse_source_file(code, '.ts')
        assert result.success
        assert result.language == 'typescript'
        assert len(result.functions) >= 2

    def test_parse_typescript_class(self):
        """Test extracting TypeScript classes."""
        code = '''
export class UserService extends BaseService implements IUserService {
    private users: User[] = [];

    async getUser(id: string): Promise<User> {
        return this.users.find(u => u.id === id);
    }
}

interface IUserService {
    getUser(id: string): Promise<User>;
}
'''
        result = parse_source_file(code, '.ts')
        assert result.success
        assert len(result.classes) >= 1

        cls = result.classes[0]
        assert cls.name == 'UserService'
        assert 'BaseService' in cls.parent_classes
        assert 'IUserService' in cls.interfaces

    def test_parse_typescript_imports(self):
        """Test extracting TypeScript imports."""
        code = '''
import React from 'react';
import { useState, useEffect } from 'react';
import type { User } from './types';
'''
        result = parse_source_file(code, '.ts')
        assert result.success
        assert len(result.imports) >= 2


class TestGoParsing:
    """Tests for Go AST extraction."""

    def test_parse_go_function(self):
        """Test extracting Go functions."""
        code = '''
package main

import "fmt"

func main() {
    fmt.Println("Hello")
}

func (s *Server) HandleRequest(w http.ResponseWriter, r *http.Request) {
    // method
}
'''
        result = parse_source_file(code, '.go')
        assert result.success
        assert result.language == 'go'
        assert len(result.functions) >= 2

        main_func = next((f for f in result.functions if f.name == 'main'), None)
        assert main_func is not None

        method = next((f for f in result.functions if f.name == 'HandleRequest'), None)
        assert method is not None
        assert method.is_method is True

    def test_parse_go_struct(self):
        """Test extracting Go structs."""
        code = '''
package main

type Server struct {
    host string
    port int
}

type Config struct {
    Debug bool
}
'''
        result = parse_source_file(code, '.go')
        assert result.success
        assert len(result.classes) >= 2

    def test_parse_go_imports(self):
        """Test extracting Go imports."""
        code = '''
package main

import (
    "fmt"
    "net/http"
    log "github.com/sirupsen/logrus"
)
'''
        result = parse_source_file(code, '.go')
        assert result.success
        assert len(result.imports) >= 2


class TestRustParsing:
    """Tests for Rust AST extraction."""

    def test_parse_rust_function(self):
        """Test extracting Rust functions."""
        code = '''
fn main() {
    println!("Hello");
}

async fn fetch_data() -> Result<(), Error> {
    Ok(())
}

pub fn public_func(x: i32) -> i32 {
    x * 2
}
'''
        result = parse_source_file(code, '.rs')
        assert result.success
        assert result.language == 'rust'
        assert len(result.functions) >= 3

        async_func = next((f for f in result.functions if f.name == 'fetch_data'), None)
        assert async_func is not None
        assert async_func.is_async is True

    def test_parse_rust_struct(self):
        """Test extracting Rust structs and enums."""
        code = '''
struct Point {
    x: f64,
    y: f64,
}

enum Color {
    Red,
    Green,
    Blue,
}

trait Drawable {
    fn draw(&self);
}
'''
        result = parse_source_file(code, '.rs')
        assert result.success
        assert len(result.classes) >= 2

    def test_parse_rust_use(self):
        """Test extracting Rust use statements."""
        code = '''
use std::io::Result;
use tokio::sync::mpsc;
use crate::config::Config;
'''
        result = parse_source_file(code, '.rs')
        assert result.success
        assert len(result.imports) >= 2


class TestJavaParsing:
    """Tests for Java AST extraction."""

    def test_parse_java_method(self):
        """Test extracting Java methods."""
        code = '''
public class Main {
    public static void main(String[] args) {
        System.out.println("Hello");
    }

    private int calculate(int x) {
        return x * 2;
    }
}
'''
        result = parse_source_file(code, '.java')
        assert result.success
        assert result.language == 'java'
        assert len(result.functions) >= 2

    def test_parse_java_class(self):
        """Test extracting Java classes."""
        code = '''
public class UserService extends BaseService implements IUserService {
    private List<User> users;

    public User getUser(String id) {
        return null;
    }
}

interface IUserService {
    User getUser(String id);
}
'''
        result = parse_source_file(code, '.java')
        assert result.success
        assert len(result.classes) >= 1

        cls = result.classes[0]
        assert cls.name == 'UserService'

    def test_parse_java_imports(self):
        """Test extracting Java imports."""
        code = '''
package com.example;

import java.util.List;
import java.util.Map;
import com.example.models.User;
'''
        result = parse_source_file(code, '.java')
        assert result.success
        assert len(result.imports) >= 2


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_empty_file(self):
        """Test parsing empty file."""
        result = parse_source_file('', '.py')
        assert result.success
        assert len(result.functions) == 0
        assert len(result.classes) == 0

    def test_unsupported_extension(self):
        """Test unsupported file extension."""
        result = parse_source_file('content', '.xyz')
        assert result.success is False
        assert 'Unsupported' in (result.error or '')

    def test_syntax_error_handling(self):
        """Test handling of syntax errors (should still parse partially)."""
        code = '''
def valid_function():
    pass

def broken_function(
    # missing closing paren
'''
        result = parse_source_file(code, '.py')
        # Tree-sitter is error-tolerant, should still find valid_function
        assert len(result.functions) >= 1

    def test_unicode_content(self):
        """Test handling of unicode content."""
        code = '''
def greet():
    """Say こんにちは."""
    print("Hello 世界! 🌍")
'''
        result = parse_source_file(code, '.py')
        assert result.success
        assert len(result.functions) == 1


class TestCallExtraction:
    """Tests for function call extraction."""

    def test_extract_python_calls(self):
        """Test extracting function calls in Python."""
        code = '''
def main():
    result = helper_func()
    process(result)
    obj.method()
'''
        result = parse_source_file(code, '.py')
        assert result.success
        assert len(result.calls) >= 3

    def test_extract_typescript_calls(self):
        """Test extracting function calls in TypeScript."""
        code = '''
function main() {
    const data = fetchData();
    process(data);
    console.log(data);
}
'''
        result = parse_source_file(code, '.ts')
        assert result.success
        assert len(result.calls) >= 3
