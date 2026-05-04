# Public Assets

This directory contains static assets that are served directly by the web server.

## Structure

```
public/
├── index.html        # Main HTML template
├── favicon.ico       # Website favicon
├── manifest.json     # Web app manifest
├── robots.txt        # Search engine directives
└── README.md         # This file
```

## Asset Types

Public directory contains:
- HTML files
- Images not processed by the build system
- Fonts
- Icons
- Manifest files
- Robot.txt files

## Important Notes

Files in this directory:
- Are served at the root of the domain
- Are not processed by the build system
- Should be referenced with absolute paths
- Are copied directly to the build output

## Referencing Assets

To reference assets in this directory:
- Use absolute paths: `/favicon.ico`
- Do not use relative paths
- Do not import in JavaScript files

## Best Practices

When adding assets to this directory:
- Optimize images for web use
- Use appropriate file formats
- Maintain consistent naming conventions
- Update references when filenames change