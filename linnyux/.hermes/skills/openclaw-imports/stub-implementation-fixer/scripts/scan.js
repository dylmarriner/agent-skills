#!/usr/bin/env node

/**
 * Stub Implementation Scanner
 * 
 * Scans codebase for incomplete implementations, scaffolded code,
 * placeholder content, mock data, TODOs, FIXMEs that need real implementation.
 */

const fs = require('fs');
const path = require('path');

class StubScanner {
  constructor(projectRoot, patterns = {}) {
    this.projectRoot = path.resolve(projectRoot);
    this.findings = [];
    this.defaultPatterns = {
      // Development markers
      todo: {
        pattern: /(?:^|\s)(TODO|FIXME|XXX|HACK|BUG|DEPRECATED|STUB|NOTE)\b.*/gi,
        priority: 'high',
        category: 'dev-marker',
        description: 'Development TODO/FIXME markers'
      },
      
      // Scaffolded and placeholder content
      scaffolded: {
        pattern: /scaffold(ed)?/gi,
        priority: 'high',
        category: 'scaffolded',
        description: 'Scaffolded content'
      },
      
      stub: {
        pattern: /\bstub\b|\bmock\b|\bplaceholder\b/gi,
        priority: 'high',
        category: 'placeholder',
        description: 'Stub and mock references'
      },
      
      // Implementation gaps
      notImplemented: {
        pattern: /not\s+implemented|throw\s+new\s+Error\(["'][^"']*not\s+implemented[^"']*["']\)|unimplemented/gi,
        priority: 'critical',
        category: 'implementation-gap',
        description: 'Functions marked as not implemented'
      },
      
      emptyFunction: {
        pattern: /(function\s+\w+\s*\([^)]*\)\s*\{\s*\})|(\w+\s*=>\s*\{\s*\})/g,
        priority: 'medium',
        category: 'implementation-gap',
        description: 'Empty function implementations'
      },
      
      // Placeholder content
      scaffoldedText: {
        pattern: /Scaffolded from the monorepo roadmap/gi,
        priority: 'high',
        category: 'scaffolded',
        description: 'Monorepo scaffold text'
      },
      
      websiteScaffold: {
        pattern: /Website scaffold page/gi,
        priority: 'high',
        category: 'scaffolded',
        description: 'Website scaffold page text'
      },
      
      // Minimal stubs and simplified code
      minimalStub: {
        pattern: /export default function \w+\(\)\s*\{\s*return <main>.*?<\/main>\s*;/s,
        priority: 'high',
        category: 'simplified',
        description: 'Minimal React stub components'
      },
      
      oneLineStub: {
        pattern: /export default function \w+\(\)\s*\{[^}]*Scaffolded[^}]*\}/g,
        priority: 'high',
        category: 'simplified',
        description: 'One-liner scaffolded functions'
      },
      
      // Mock data patterns
      mockUserData: {
        pattern: /["']name["']:\s*["'][^"']*Doe\s*Smith\s*[^"']*["'].*?["']email["']:\s*["'][^"']*@example\.com\s*["']/gi,
        priority: 'medium',
        category: 'mock-data',
        description: 'Mock user data with example.com'
      },
      
      mockApi: {
        pattern: /return\s*\[.*?(?:id:\s*\d+.*?(?:name:\s*["'][^"']+["'])?).*?\]/gs,
        priority: 'medium',
        category: 'mock-data',
        description: 'Mock API responses with hardcoded data'
      },
      
      // Configuration placeholders
      placeholderValue: {
        pattern: /(example\.com|localhost|your-|todo@example\.com|placeholder|example\.com)/gi,
        priority: 'low',
        category: 'placeholder',
        description: 'Placeholder configuration values'
      },
      
      defaultExample: {
        pattern: /example|placeholder/gi,
        priority: 'low',
        category: 'placeholder',
        description: 'Default example values'
      },
      
      // Simplified logic
      hardcodedData: {
        pattern: /(?:return|const\s+\w+\s*=\s*)\{[^}]*(?:name|email|url|api)[^}]*\}/gi,
        priority: 'medium',
        category: 'simplified',
        description: 'Hardcoded data structures'
      },
      
      simplifiedValidation: {
        pattern: /\b(?:if\s*\([^)]*\)\s*\{[^}]*\})\s*else\s*\{[^}]*\}\s*$/gm,
        priority: 'low',
        category: 'simplified',
        description: 'Simplified validation logic'
      },
      
      // Documentation placeholders
      emptyReadme: {
        pattern: /^# \w+[\w\s]*\n\n## (Installation|Usage|Setup)\n\n\[\w+.*?\]\(\w+.*?\)\n\n$/gm,
        priority: 'medium',
        category: 'documentation',
        description: 'README with placeholder sections'
      },
      
      placeholderDoc: {
        pattern: /\[Instructions here\]|\(TODO:.*?\)|placeholder.*?here/gi,
        priority: 'medium',
        category: 'documentation',
        description: 'Placeholder documentation'
      }
    };
    
    // Merge custom patterns
    this.patterns = { ...this.defaultPatterns, ...patterns };
    
    // Directories to exclude
    this.excludePatterns = [
      /node_modules/,
      /\.git/,
      /dist/,
      /build/,
      /\.next/,
      /coverage/,
      /\.cache/,
      /vendor/,
      /\.venv/,
      /__pycache__/,
      /\.pytest_cache/,
      /\.dockerenv/,
      /Docker\.file/,
    ];
  }

  shouldExclude(filePath) {
    return this.excludePatterns.some(pattern => pattern.test(filePath));
  }

  getFileType(ext) {
    const typeMap = {
      '.js': 'javascript',
      '.jsx': 'react',
      '.ts': 'typescript',
      '.tsx': 'react',
      '.py': 'python',
      '.go': 'go',
      '.java': 'java',
      '.cpp': 'cpp',
      '.c': 'c',
      '.h': 'c',
      '.rb': 'ruby',
      '.php': 'php',
      '.rs': 'rust',
      '.swift': 'swift',
      '.kt': 'kotlin',
      '.scala': 'scala',
      '.md': 'markdown',
      '.yml': 'yaml',
      '.yaml': 'yaml',
      '.json': 'json',
      '.css': 'css',
      '.scss': 'scss',
      '.less': 'less',
      '.html': 'html',
      '.xml': 'xml',
    };
    return typeMap[ext] || 'unknown';
  }

  async scan() {
    console.log('🔍 Scanning for stub implementations, TODOs, FIXMEs, and mock data...');
    
    await this.walkDirectory(this.projectRoot);
    
    return this.findings;
  }

  async walkDirectory(dir) {
    const entries = fs.readdirSync(dir, { withFileTypes: true });
    
    for (const entry of entries) {
      const fullPath = path.join(dir, entry.name);
      
      if (entry.isDirectory()) {
        if (!this.shouldExclude(fullPath)) {
          await this.walkDirectory(fullPath);
        }
      } else if (entry.isFile()) {
        await this.scanFile(fullPath);
      }
    }
  }

  async scanFile(filePath) {
    try {
      const content = fs.readFileSync(filePath, 'utf8');
      const relativePath = path.relative(this.projectRoot, filePath);
      const ext = path.extname(filePath).toLowerCase();
      
      const matches = this.findPatterns(content, filePath);
      
      if (matches.length > 0) {
        this.findings.push({
          file: relativePath,
          path: filePath,
          size: content.length,
          lines: content.split('\n').length,
          type: this.getFileType(ext),
          ext,
          matches: matches,
          priority: this.calculateFilePriority(matches),
        });
      }
    } catch (error) {
      // Skip files that can't be read (binary, permissions, etc.)
    }
  }

  calculateFilePriority(matches) {
    const priorities = {
      'critical': 4,
      'high': 3,
      'medium': 2,
      'low': 1
    };

    let maxPriority = 0;
    for (const match of matches) {
      const priority = priorities[match.priority] || 1;
      maxPriority = Math.max(maxPriority, priority);
    }

    const priorityKeys = Object.keys(priorities);
    for (let i = priorityKeys.length - 1; i >= 0; i--) {
      if (priorities[priorityKeys[i]] <= maxPriority) {
        return priorityKeys[i];
      }
    }
    return 'low';
  }

  findPatterns(content, filePath) {
    const findings = [];
    const ext = path.extname(filePath).toLowerCase();
    
    // Check each pattern
    Object.entries(this.patterns).forEach(([patternName, config]) => {
      const matches = [...content.matchAll(new RegExp(config.pattern, 'gi'))];
      
      if (matches.length > 0) {
        // Filter out false positives based on file type and context
        const relevantMatches = this.filterMatches(
          matches,
          { ...config, patternName },
          ext,
          content,
          matches.length
        );
        
        if (relevantMatches.length > 0) {
          findings.push({
            pattern: patternName,
            category: config.category,
            priority: config.priority,
            description: config.description,
            count: relevantMatches.length,
            matches: relevantMatches,
          });
        }
      }
    });
    
    return findings;
  }

  filterMatches(matches, config, ext, content, totalMatches) {
    return matches.filter((match, index) => {
      const globalIndex = match.index;
      const context = this.getContext(content, globalIndex);
      
      // Skip if in comments (for patterns that shouldn't be in comments)
      if (this.isInComment(context, ext) && !['todo'].includes(config.patternName)) {
        return false;
      }
      
      // Pattern-specific filters
      switch (config.patternName) {
        case 'emptyFunction':
          return !this.isEmptyUtilityFunction(match) && !this.isEmptyArrowFunction(match);
        case 'minimalStub':
          return this.isReactComponentStub(match, content);
        case 'mockUserData':
          return this.isMockUserContext(match, content);
        case 'placeholderValue':
          return !this.isInValidContext(match, content);
        default:
          return true;
      }
    });
  }

  getContext(content, index, contextSize = 100) {
    const start = Math.max(0, index - contextSize);
    const end = Math.min(content.length, index + contextSize);
    return content.substring(start, end);
  }

  isInComment(context, ext) {
    // Simple comment detection for common file types
    const commentPatterns = {
      '.js': /\/\*|\/\//,
      '.ts': /\/\*|\/\//,
      '.jsx': /\/\*|\/\//,
      '.tsx': /\/\*|\/\//,
      '.py': /#/,
      '.go': /\/\*|\/\//,
      '.java': /\/\*|\/\//,
      '.cpp': /\/\*|\/\//,
    };
    
    const pattern = commentPatterns[ext];
    if (!pattern) return false;
    
    return pattern.test(context);
  }

  isEmptyUtilityFunction(match) {
    const context = match.input.substring(
      match.index - 50,
      match.index + 150
    );
    
    // Common empty utility functions that are legitimate
    return /function\s+(noop|identity|pure|empty|init)\s*\(/i.test(context) ||
           /=>\s*\{\s*\}/.test(context) ||
           /const\s+\w+\s*=\s*\(\)\s*=>\s*\{\s*\}/.test(context);
  }

  isEmptyArrowFunction(match) {
    const context = match.input.substring(
      match.index - 30,
      match.index + 100
    );
    
    // Check for legitimate empty arrow functions
    return /(const\s+\w+\s*=\s*\(\)\s*=>\s*\{\s*\}|\w+\s*=\s*\(\)\s*=>\s*\{\s*\})/.test(context);
  }

  isReactComponentStub(match, content) {
    const context = match.input.substring(
      match.index - 20,
      match.index + 200
    );
    
    return /Scaffold|scaffold|stub/i.test(context) ||
           /export default function Page/.test(context) ||
           /return <main>/.test(context);
  }

  isMockUserContext(match, content) {
    const context = match.input.substring(
      match.index - 50,
      match.index + 100
    );
    
    return /user|demo|test|fake|mock/i.test(context);
  }

  isInValidContext(match, content) {
    const context = match.input.substring(
      match.index - 30,
      match.index + 30
    );
    
    // Skip if it's in a URL or comment
    return /url|href|src/i.test(context) && !/placeholder|example/i.test(context);
  }

  generateReport() {
    const report = {
      totalFiles: this.findings.length,
      totalIssues: this.findings.reduce((sum, f) => 
        sum + f.matches.reduce((s, m) => s + m.count, 0), 0
      ),
      findings: this.findings,
      summary: {
        byCategory: {},
        byPriority: {},
        byType: {},
      },
      critical: [],
      high: [],
      requiresReview: []
    };
    
    // Generate summary statistics
    this.findings.forEach(file => {
      // By category
      file.matches.forEach(match => {
        report.summary.byCategory[match.category] = 
          (report.summary.byCategory[match.category] || 0) + match.count;
      });
      
      // By priority
      report.summary.byPriority[file.priority] = 
        (report.summary.byPriority[file.priority] || 0) + 1;
      
      // By file type
      report.summary.byType[file.type] = 
        (report.summary.byType[file.type] || 0) + 1;
    });
    
    // Separate by priority
    this.findings.forEach(file => {
      const fileEntry = {
        file: file.file,
        issueCount: file.matches.reduce((sum, m) => sum + m.count, 0),
        issues: file.matches
      };
      
      if (file.priority === 'critical') {
        report.critical.push(fileEntry);
      } else if (file.priority === 'high') {
        report.high.push(fileEntry);
      }
    });
    
    return report;
  }
}

// CLI usage
if (require.main === module) {
  const args = process.argv.slice(2);
  const projectRoot = args[0] || '.';
  const patternsFile = args[1];
  
  let customPatterns = {};
  if (patternsFile && fs.existsSync(patternsFile)) {
    customPatterns = JSON.parse(fs.readFileSync(patternsFile, 'utf8'));
  }
  
  const scanner = new StubScanner(projectRoot, customPatterns);
  
  scanner.scan().then(() => {
    const report = scanner.generateReport();
    console.log('\n📊 Scan Results:');
    console.log(`  Files with issues: ${report.totalFiles}`);
    console.log(`  Total issues found: ${report.totalIssues}`);
    
    console.log('\nBy category:');
    Object.entries(report.summary.byCategory).forEach(([category, count]) => {
      console.log(`  ${category}: ${count}`);
    });
    
    console.log('\nBy priority:');
    Object.entries(report.summary.byPriority).forEach(([priority, count]) => {
      console.log(`  ${priority}: ${count} files`);
    });
    
    console.log('\n❗ Critical Issues:');
    report.critical.forEach(finding => {
      console.log(`  ${finding.file} (${finding.issueCount} issues)`);
      finding.issues.forEach(issue => {
        console.log(`    - ${issue.description}`);
      });
    });
    
    console.log('\n⚠️  High Priority Issues:');
    report.high.forEach(finding => {
      console.log(`  ${finding.file} (${finding.issueCount} issues)`);
      finding.issues.slice(0, 3).forEach(issue => {
        console.log(`    - ${issue.description}`);
      });
      if (finding.issues.length > 3) {
        console.log(`    ... and ${finding.issues.length - 3} more`);
      }
    });
    
    // Save detailed report
    fs.writeFileSync(
      path.join(projectRoot, 'stub-scan-report.json'),
      JSON.stringify(report, null, 2)
    );
    
    console.log('\n✅ Detailed report saved to: stub-scan-report.json');
  });
}

module.exports = StubScanner;
