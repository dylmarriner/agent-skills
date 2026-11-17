#!/usr/bin/env node

/**
 * Stub Implementation Fixer - Main Entry Point
 * 
 * Orchestrates the entire process: scanning, analysis, and implementation
 * of missing code, TODOs, FIXMEs, and mock data.
 */

const path = require('path');
const StubScanner = require('./scan');
const StubImplementationEngine = require('./implement');

class StubImplementationFixer {
  constructor(projectRoot, options = {}) {
    this.projectRoot = path.resolve(projectRoot);
    this.options = {
      autoScan: true,
      autoImplement: true,
      dryRun: false,
      backup: true,
      patterns: 'all',
      outputDir: '.stub-results',
      ...options
    };
    this.scanner = null;
    this.engine = null;
  }

  async fix(options = {}) {
    const runOptions = { ...this.options, ...options };
    console.log('🚀 Stub Implementation Fixer Starting...\n');

    try {
      // Create output directory
      const outputDir = path.join(this.projectRoot, runOptions.outputDir);
      require('fs').mkdirSync(outputDir, { recursive: true });

      // Phase 1: Scan
      if (runOptions.autoScan) {
        console.log('Phase 1: Scanning for stub implementations...');
        this.scanner = new StubScanner(this.projectRoot);
        const scanResults = await this.scanner.scan();
        
        if (scanResults.length === 0) {
          console.log('✅ No stub implementations found!');
          return { scan: null, implementation: null };
        }

        const scanReport = this.scanner.generateReport();
        console.log(`\n✅ Scan complete: ${scanReport.totalFiles} files, ${scanReport.totalIssues} issues found\n`);

        // Save scan results
        const scanPath = path.join(outputDir, 'scan-results.json');
        require('fs').writeFileSync(scanPath, JSON.stringify(scanReport, null, 2));
        console.log(`📄 Scan results saved to: ${scanPath}`);
        
        // Show summary
        console.log('\n📊 Summary:');
        Object.entries(scanReport.summary.byCategory).forEach(([category, count]) => {
          console.log(`  ${category}: ${count}`);
        });

        // Phase 2: Implementation
        if (runOptions.autoImplement && !runOptions.dryRun) {
          console.log('\nPhase 2: Implementing fixes...\n');
          this.engine = new StubImplementationEngine(this.projectRoot, scanReport, runOptions);
          const implementationResults = await this.engine.process();
          
          // Save implementation report
          const implPath = path.join(outputDir, 'implementation-report.json');
          require('fs').writeFileSync(implPath, JSON.stringify(implementationResults, null, 2));
          console.log(`\n📄 Implementation report saved to: ${implPath}`);
          
          return { scan: scanReport, implementation: implementationResults };
        } else if (runOptions.autoImplement && runOptions.dryRun) {
          console.log('\nPhase 2: Dry run - would implement fixes...\n');
          this.engine = new StubImplementationEngine(this.projectRoot, scanReport, runOptions);
          const implementationResults = await this.engine.process();
          
          console.log('\n📄 Dry run complete. No files were modified.');
          return { scan: scanReport, implementation: implementationResults };
        }
      }

    } catch (error) {
      console.error('❌ Error during stub implementation:', error);
      throw error;
    }
  }

  async scanOnly(options = {}) {
    const scanOptions = { ...this.options, ...options };
    console.log('🔍 Scan Mode: Finding stub implementations...\n');

    this.scanner = new StubScanner(this.projectRoot);
    const scanResults = await this.scanner.scan();
    
    if (scanResults.length === 0) {
      console.log('✅ No stub implementations found!');
      return { scan: null };
    }

    const scanReport = this.scanner.generateReport();
    
    // Save results
    const outputDir = path.join(this.projectRoot, scanOptions.outputDir);
    require('fs').mkdirSync(outputDir, { recursive: true });
    
    const scanPath = path.join(outputDir, 'scan-results.json');
    require('fs').writeFileSync(scanPath, JSON.stringify(scanReport, null, 2));
    
    console.log(`\n✅ Scan Results: ${scanReport.totalFiles} files, ${scanReport.totalIssues} issues`);
    console.log(`📄 Results saved to: ${scanPath}`);
    
    return { scan: scanReport };
  }

  async implementOnly(scanResultsFile, options = {}) {
    const implOptions = { ...this.options, ...options };
    console.log('🔧 Implementation Mode: Applying fixes...\n');

    if (!scanResultsFile || !require('fs').existsSync(scanResultsFile)) {
      throw new Error('Please provide a valid scan results file');
    }

    const scanResults = JSON.parse(require('fs').readFileSync(scanResultsFile, 'utf8'));
    
    this.engine = new StubImplementationEngine(this.projectRoot, scanResults, implOptions);
    const implementationResults = await this.engine.process();
    
    // Save results
    const outputDir = path.join(this.projectRoot, implOptions.outputDir);
    require('fs').mkdirSync(outputDir, { recursive: true });
    
    const implPath = path.join(outputDir, 'implementation-report.json');
    require('fs').writeFileSync(implPath, JSON.stringify(implementationResults, null, 2));
    
    return { implementation: implementationResults };
  }
}

// CLI usage
if (require.main === module) {
  const args = process.argv.slice(2);
  
  if (args.length === 0) {
    console.log(`
Stub Implementation Fixer

Usage:
  node index.js [project-root] [options]

Options:
  --scan-only           Only scan, don't implement
  --implement FILE      Implement fixes from scan results file
  --dry-run            Preview changes without applying them
  --no-backup          Don't create backup files
  --patterns PATTERNS  Comma-separated list of patterns to focus on
                       (all, todo, fixme, mock-data, placeholder, etc.)
  --output-dir DIR     Directory for output files (default: .stub-results)

Examples:
  # Full scan and implementation
  node index.js /path/to/project
  
  # Scan only
  node index.js /path/to/project --scan-only
  
  # Implement from previous scan
  node index.js --implement .stub-results/scan-results.json
  
  # Dry run
  node index.js --dry-run
  
  # Focus on specific patterns
  node index.js --patterns "todo,fixme,mock-data"
    `);
    process.exit(0);
  }

  const projectRoot = args[0].startsWith('--') ? '.' : args[0];
  const options = {
    scanOnly: args.includes('--scan-only'),
    implement: args.find(arg => arg.startsWith('--implement') && !arg.includes('.')) ? args.find(arg => arg.startsWith('--implement')).split('=')[1] : null,
    dryRun: args.includes('--dry-run'),
    backup: !args.includes('--no-backup'),
    patterns: args.find(arg => arg.startsWith('--patterns'))?.split('=')[1] || 'all',
    outputDir: args.find(arg => arg.startsWith('--output-dir'))?.split('=')[1] || '.stub-results'
  };

  const fixer = new StubImplementationFixer(projectRoot, options);

  fixer.fix().then(results => {
    console.log('\n✅ Stub Implementation Fixer completed successfully!');
    
    if (results.implementation) {
      console.log(`\n📊 Final Summary:`);
      console.log(`  Files changed: ${results.implementation.summary.filesChanged}`);
      console.log(`  Total changes: ${results.implementation.summary.totalChanges}`);
    }
    
    process.exit(0);
  }).catch(error => {
    console.error('\n❌ Stub Implementation Fixer failed:', error);
    process.exit(1);
  });
}

module.exports = StubImplementationFixer;
