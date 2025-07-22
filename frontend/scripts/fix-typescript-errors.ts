#!/usr/bin/env node

/**
 * Script to help identify and fix common TypeScript errors
 * Run with: tsx scripts/fix-typescript-errors.ts
 */

import { execSync } from 'child_process';
import fs from 'fs';
import path from 'path';

interface TypeScriptError {
  code: string;
  message: string;
  file: string;
  line: number;
}

console.log('🔍 Checking for TypeScript errors...\n');

try {
  // Run TypeScript compiler to get all errors
  const result = execSync('npx tsc --noEmit', { 
    encoding: 'utf8',
    cwd: process.cwd()
  });
  
  console.log('✅ No TypeScript errors found!');
  
} catch (error: any) {
  const errorOutput: string = error.stdout || error.stderr || '';
  
  if (errorOutput.includes('error TS7031')) {
    console.log('🚨 Found binding elements with implicit "any" type:\n');
    
    const implicitAnyErrors: string[] = errorOutput
      .split('\n')
      .filter((line: string) => line.includes('error TS7031'))
      .slice(0, 10); // Show first 10 errors
    
    implicitAnyErrors.forEach((error: string) => {
      console.log(`   ${error}`);
    });
    
    console.log('\n📝 Common fixes:');
    console.log('   1. Add interface for component props:');
    console.log('      interface Props { prop1: string; prop2: number; }');
    console.log('      const Component = ({ prop1, prop2 }: Props) => {}');
    console.log('');
    console.log('   2. Add types to function parameters:');
    console.log('      const handleClick = (e: React.MouseEvent) => {}');
    console.log('      const onChange = (e: React.ChangeEvent<HTMLInputElement>) => {}');
    console.log('');
  }
  
  if (errorOutput.includes('error TS7006')) {
    console.log('🚨 Found parameters with implicit "any" type:\n');
    
    const parameterErrors: string[] = errorOutput
      .split('\n')
      .filter((line: string) => line.includes('error TS7006'))
      .slice(0, 5); // Show first 5 errors
    
    parameterErrors.forEach((error: string) => {
      console.log(`   ${error}`);
    });
    
    console.log('\n📝 Common fixes:');
    console.log('   1. Add types to callback parameters:');
    console.log('      .map((item: Item) => item.name)');
    console.log('      .forEach((item: Item, index: number) => {})');
    console.log('');
  }
  
  if (errorOutput.includes('error TS2339')) {
    console.log('🚨 Found property access errors:\n');
    
    const propertyErrors: string[] = errorOutput
      .split('\n')
      .filter((line: string) => line.includes('error TS2339'))
      .slice(0, 5); // Show first 5 errors
    
    propertyErrors.forEach((error: string) => {
      console.log(`   ${error}`);
    });
    
    console.log('\n📝 Common fixes:');
    console.log('   1. Add missing properties to interface');
    console.log('   2. Use optional chaining: obj?.property');
    console.log('   3. Use type assertion: (obj as any).property');
    console.log('');
  }
  
  console.log('\n🔧 To fix these errors:');
  console.log('   1. Run: npm run build (to see if they affect the build)');
  console.log('   2. Add type annotations to components and functions');
  console.log('   3. Create interfaces for complex objects');
  console.log('   4. Use React.FC<Props> for functional components');
  console.log('');
  console.log('💡 Example component with proper types:');
  console.log(`
interface ButtonProps {
  onClick: () => void;
  children: React.ReactNode;
  variant?: 'primary' | 'secondary';
}

const Button: React.FC<ButtonProps> = ({ onClick, children, variant = 'primary' }) => {
  return (
    <button onClick={onClick} className={\`btn btn-\${variant}\`}>
      {children}
    </button>
  );
};
`);
}

console.log('\n🎯 Priority fixes:');
console.log('   1. Fix components with props (highest impact)');
console.log('   2. Fix event handlers and callbacks');
console.log('   3. Fix utility functions and hooks');
console.log('   4. Add stricter TypeScript rules gradually');