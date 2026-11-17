/**
 * Project Templates for Stub Implementation
 * 
 * Contains template implementations for common patterns found in projects.
 * These templates are used to replace stubbed code with production-ready versions.
 */

module.exports = {
  // React Component Templates
  react: {
    pageComponent: `import React from 'react';

export default function {{ComponentName}}() {
  return (
    <div className=\"min-h-screen bg-gray-50\">
      <div className=\"max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12\">
        <div className=\"text-center\">
          <h1 className=\"text-4xl font-extrabold text-gray-900 sm:text-5xl\">
            {{PageTitle}}
          </h1>
          <p className=\"mt-4 text-xl text-gray-600\">
            {{PageDescription}}
          </p>
        </div>
        
        <div className=\"mt-12\">
          <div className=\"bg-white shadow rounded-lg p-6\">
            <h2 className=\"text-2xl font-semibold text-gray-900 mb-4\">
              {{SectionTitle}}
            </h2>
            <p className=\"text-gray-600\">
              {{SectionContent}}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}`,

    functionalComponent: `import React from 'react';

export const {{ComponentName}} = () => {
  return (
    <div className=\"{{ComponentName}}\">
      <p>TODO: Implement {{ComponentName}} functionality</p>
    </div>
  );
};`
  },

  // API Endpoint Templates  
  api: {
    express: `const express = require('express');
const router = express.Router();

/**
 * {{EndpointDescription}}
 * @route {{HttpMethod}} {{Route}}
 * @description {{EndpointDescription}}
 */
router.{{method}}('{{route}}', async (req, res) => {
  try {
    // Validation
    const validationResult = await validateRequest(req.body);
    if (!validationResult.isValid) {
      return res.status(400).json({
        success: false,
        error: 'Validation failed',
        details: validationResult.errors
      });
    }

    // Business logic
    const result = await processRequest(req.body);
    
    res.json({
      success: true,
      data: result,
      message: '{{SuccessMessage}}'
    });
  } catch (error) {
    console.error('{{MethodName}} error:', error);
    
    res.status(500).json({
      success: false,
      error: 'Internal server error',
      message: 'An unexpected error occurred'
    });
  }
});

module.exports = router;`,

    generic: `/**
 * {{FunctionDescription}}
 */
async function {{FunctionName}}({{Params}}) {
  try {
    // Input validation
    if (!{{Params}}) {
      throw new Error('{{ParamErrorMessage}}');
    }

    // Main logic
    const result = await performOperation({{Params}});
    
    // Success response
    return {
      success: true,
      data: result,
      timestamp: new Date().toISOString()
    };
  } catch (error) {
    console.error('{{FunctionName}} error:', error);
    
    return {
      success: false,
      error: error.message,
      timestamp: new Date().toISOString()
    };
  }
}

module.exports = { {{FunctionName}} };`
  },

  // Database/Model Templates
  database: {
    schema: `/**
 * {{ModelName}} Model Schema
 * 
 * Represents the structure and validation for {{ModelDescription}}
 */
const mongoose = require('mongoose');

const {{ModelName}}Schema = new mongoose.Schema({
  {{Fields}}
}, {
  timestamps: true,
  collection: '{{CollectionName}}'
});

// Indexes
{{Indexes}}

// Virtuals
{{Virtuals}}

// Methods
{{ModelName}}Schema.methods = {
  async {{MethodName}}({{Params}}) {
    // Implement method logic
  }
};

// Static methods
{{ModelName}}Schema.statics = {
  async {{StaticMethodName}}({{Params}}) {
    // Implement static method logic
  }
};

module.exports = mongoose.model('{{ModelName}}', {{ModelName}}Schema);`,

    repository: `/**
 * {{ModelName}} Repository
 * 
 * Data access layer for {{ModelDescription}}
 */
const {{ModelName}} = require('../models/{{ModelName}}');

class {{ModelName}}Repository {
  /**
   * Create a new {{ModelName}}
   */
  async create(data) {
    try {
      // Validate input
      this.validateInput(data);
      
      // Create and save
      const {{ModelNameLower}} = new {{ModelName}}(data);
      const saved = await {{ModelNameLower}}.save();
      
      return {
        success: true,
        data: saved,
        message: '{{ModelName}} created successfully'
      };
    } catch (error) {
      console.error('{{ModelName}} creation error:', error);
      throw new Error('Failed to create {{ModelName}}');
    }
  }

  /**
   * Find {{ModelName}} by ID
   */
  async findById(id) {
    try {
      if (!id) {
        throw new Error('ID is required');
      }

      const {{ModelNameLower}} = await {{ModelName}}.findById(id).populate('{{PopulatePaths}}');
      
      if (!{{ModelNameLower}}) {
        return {
          success: false,
          message: '{{ModelName}} not found'
        };
      }

      return {
        success: true,
        data: {{ModelNameLower}},
        message: '{{ModelName}} retrieved successfully'
      };
    } catch (error) {
      console.error('{{ModelName}} retrieval error:', error);
      throw error;
    }
  }

  /**
   * Update {{ModelName}}
   */
  async update(id, data) {
    try {
      if (!id) {
        throw new Error('ID is required');
      }

      // Validate input
      this.validateInput(data);
      
      const updated = await {{ModelName}}.findByIdAndUpdate(
        id,
        { ...data, updatedAt: new Date() },
        { new: true, runValidators: true }
      );

      if (!updated) {
        return {
          success: false,
          message: '{{ModelName}} not found'
        };
      }

      return {
        success: true,
        data: updated,
        message: '{{ModelName}} updated successfully'
      };
    } catch (error) {
      console.error('{{ModelName}} update error:', error);
      throw error;
    }
  }

  /**
   * Delete {{ModelName}}
   */
  async delete(id) {
    try {
      if (!id) {
        throw new Error('ID is required');
      }

      const deleted = await {{ModelName}}.findByIdAndDelete(id);

      if (!deleted) {
        return {
          success: false,
          message: '{{ModelName}} not found'
        };
      }

      return {
        success: true,
        message: '{{ModelName}} deleted successfully'
      };
    } catch (error) {
      console.error('{{ModelName}} deletion error:', error);
      throw error;
    }
  }

  /**
   * Find all {{ModelName}} entities with pagination
   */
  async findAll(options = {}) {
    try {
      const { page = 1, limit = 10, sort = '-createdAt', ...query } = options;
      
      const skip = (page - 1) * limit;
      
      const [items, total] = await Promise.all([
        {{ModelName}}.find(query)
          .sort(sort)
          .skip(skip)
          .limit(limit)
          .populate('{{PopulatePaths}}'),
        {{ModelName}}.countDocuments(query)
      ]);

      const totalPages = Math.ceil(total / limit);

      return {
        success: true,
        data: items,
        pagination: {
          current: page,
          total: totalPages,
          count: total,
          hasNext: page < totalPages,
          hasPrev: page > 1
        },
        message: '{{ModelName}} list retrieved successfully'
      };
    } catch (error) {
      console.error('{{ModelName}} list error:', error);
      throw error;
    }
  }

  /**
   * Validate input data
   */
  validateInput(data) {
    const required = [{{RequiredFields}}];
    const missing = required.filter(field => !data[field]);
    
    if (missing.length > 0) {
      throw new Error(\`Missing required fields: \${missing.join(', ')}\`);
    }

    // Additional validation rules
    if (data.email && !this.isValidEmail(data.email)) {
      throw new Error('Invalid email format');
    }
    
    {{AdditionalValidation}}
  }

  /**
   * Utility: Email validation
   */
  isValidEmail(email) {
    const re = /^[^\\s@]+@[^\\s@]+\\.[^\\s@]+$/;
    return re.test(email);
  }
}

module.exports = new {{ModelName}}Repository();`
  },

  // Service Layer Templates
  service: `/**
 * {{ServiceName}} Service
 * 
 * Business logic layer for {{ServiceDescription}}
 */
const repository = require('../repositories/{{ModelName}}Repository');
const cache = require('../utils/cache');

class {{ServiceName}}Service {
  /**
   * {{MethodDescription}}
   */
  async {{MethodName}}({{Params}}) {
    try {
      // Business logic validation
      await this.validateBusinessRules({{Params}});
      
      // Check cache first
      const cacheKey = \`{{ServiceName}}:\${{{Params}}.id}\`;
      let result = await cache.get(cacheKey);
      
      if (!result) {
        // Perform operation
        result = await repository.{{RepositoryMethod}}({{Params}});
        
        // Cache successful results
        if (result.success) {
          await cache.set(cacheKey, result, 300000); // 5 minutes
        }
      }
      
      return result;
    } catch (error) {
      console.error('{{MethodName}} service error:', error);
      throw error;
    }
  }

  /**
   * Business rule validation
   */
  async validateBusinessRules(data) {
    // Add your specific business logic here
    if (data.status === 'invalid') {
      throw new Error('Invalid status for {{ServiceName}}');
    }
  }

  /**
   * Batch operations
   */
  async batch{{OperationName}}(operations, options = {}) {
    const results = await Promise.allSettled(
      operations.map(op => this.{{MethodName}}(op))
    );

    return {
      total: operations.length,
      successful: results.filter(r => r.status === 'fulfilled').length,
      failed: results.filter(r => r.status === 'rejected').length,
      details: results.map((r, i) => ({
        index: i,
        operation: operations[i],
        result: r.status === 'fulfilled' ? r.value : r.reason
      }))
    };
  }

  /**
   * Event processing
   */
  async processEvent(event) {
    try {
      switch (event.type) {
        case 'CREATE':
          return await this.handleCreate(event.data);
        case 'UPDATE':
          return await this.handleUpdate(event.data);
        case 'DELETE':
          return await this.handleDelete(event.data);
        default:
          throw new Error(\`Unsupported event type: \${event.type}\`);
      }
    } catch (error) {
      console.error('Event processing error:', error);
      throw error;
    }
  }

  async handleCreate(data) {
    // Handle create event
    return await this.{{MethodName}}(data);
  }

  async handleUpdate(data) {
    // Handle update event
    return await this.{{MethodName}}(data);
  }

  async handleDelete(data) {
    // Handle delete event
    return await repository.delete(data.id);
  }
}

module.exports = new {{ServiceName}}Service();`,

  // Configuration Templates
  config: {
    environment: `/**
 * Environment Configuration
 * 
 * Centralized configuration management
 */
module.exports = {
  // Database
  database: {
    url: process.env.DATABASE_URL || 'mongodb://localhost:27017/{{appName}}',
    options: {
      useNewUrlParser: true,
      useUnifiedTopology: true,
      maxPoolSize: 10,
      serverSelectionTimeoutMS: 5000,
      socketTimeoutMS: 45000,
    },
  },

  // Server
  server: {
    port: process.env.PORT || 3000,
    host: process.env.HOST || 'localhost',
    cors: {
      origin: process.env.CORS_ORIGIN?.split(',') || ['http://localhost:3000'],
      credentials: true,
    },
  },

  // Authentication
  auth: {
    jwtSecret: process.env.JWT_SECRET || 'your-super-secret-jwt-key',
    jwtExpiresIn: process.env.JWT_EXPIRES_IN || '24h',
    bcryptRounds: process.env.BCRYPT_ROUNDS || 12,
  },

  // External APIs
  apis: {
    payment: {
      key: process.env.PAYMENT_API_KEY,
      secret: process.env.PAYMENT_API_SECRET,
      baseUrl: process.env.PAYMENT_API_URL || 'https://api.stripe.com',
    },
    email: {
      key: process.env.SENDGRID_API_KEY,
      baseUrl: 'https://api.sendgrid.com/v3',
      fromEmail: process.env.FROM_EMAIL || 'noreply@{{appName}}.com',
    },
  },

  // Cache
  cache: {
    redis: {
      host: process.env.REDIS_HOST || 'localhost',
      port: process.env.REDIS_PORT || 6379,
      password: process.env.REDIS_PASSWORD,
      db: process.env.REDIS_DB || 0,
    },
  },

  // Logging
  logging: {
    level: process.env.LOG_LEVEL || 'info',
    format: process.env.LOG_FORMAT || 'combined',
  },

  // Rate limiting
  rateLimit: {
    windowMs: 15 * 60 * 1000, // 15 minutes
    max: 100, // limit each IP to 100 requests per windowMs
  },
};`,

    docker: `# Multi-stage Docker build for production optimization
FROM node:18-alpine AS builder

# Set working directory
WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci --only=production && npm cache clean --force

# Production stage
FROM node:18-alpine AS production

# Install dumb-init for proper signal handling
RUN apk add --no-cache dumb-init

# Create app user
RUN addgroup -g 1001 -S nodejs && \\
    adduser -S {{appName}} -u 1001

# Set working directory
WORKDIR /app

# Copy built application
COPY --from=builder /app/node_modules ./node_modules
COPY --chown={{appName}}:nodejs . .

# Switch to non-root user
USER {{appName}}

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \\
  CMD curl -f http://localhost:3000/health || exit 1

# Expose port
EXPOSE 3000

# Use dumb-init to handle signals properly
ENTRYPOINT ["dumb-init", "--"]

# Start application
CMD ["node", "server.js"]`
  },

  // Documentation Templates
  documentation: {
    readme: `# {{ProjectName}}

{{ProjectDescription}}

## 🚀 Features

- ✨ Modern, scalable architecture
- 🔒 Secure authentication & authorization
- 📊 Real-time data processing
- 🌐 RESTful API design
- 🧪 Comprehensive test coverage
- 📝 Comprehensive documentation

## 🛠️ Tech Stack

- **Backend:** Node.js, Express.js, MongoDB
- **Frontend:** React, TypeScript, Tailwind CSS
- **Authentication:** JWT, bcrypt
- **Database:** MongoDB with Mongoose
- **Caching:** Redis
- **Testing:** Jest, Supertest
- **Documentation:** JSDoc, OpenAPI

## 📋 Prerequisites

- Node.js (v16 or higher)
- MongoDB (v5.0 or higher)
- Redis (v6.0 or higher)
- npm or yarn

## 🚀 Quick Start

### Installation

1. **Clone the repository**
   \`\`\`bash
   git clone https://github.com/your-org/{{projectSlug}}.git
   cd {{projectSlug}}
   \`\`\`

2. **Install dependencies**
   \`\`\`bash
   npm install
   \`\`\`

3. **Environment setup**
   \`\`\`bash
   cp .env.example .env
   # Edit .env with your configuration
   \`\`\`

4. **Start development server**
   \`\`\`bash
   npm run dev
   \`\`\`

### Docker Setup (Recommended)

1. **Using Docker Compose**
   \`\`\`bash
   docker-compose up -d
   \`\`\`

2. **Manual Docker Build**
   \`\`\`bash
   docker build -t {{appName}} .
   docker run -p 3000:3000 {{appName}}
   \`\`\`

## 📚 API Documentation

### Authentication

All protected routes require a Bearer token:

\`\`\`bash
Authorization: Bearer <your-jwt-token>
\`\`\`

### Core Endpoints

#### Users
- \`GET /api/v1/users\` - List all users
- \`GET /api/v1/users/:id\` - Get user by ID
- \`POST /api/v1/users\` - Create new user
- \`PUT /api/v1/users/:id\` - Update user
- \`DELETE /api/v1/users/:id\` - Delete user

#### Authentication
- \`POST /api/v1/auth/login\` - User login
- \`POST /api/v1/auth/register\` - User registration
- \`POST /api/v1/auth/logout\` - User logout
- \`GET /api/v1/auth/profile\` - Get current user profile

### Error Handling

All API responses follow this format:

\`\`\`json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Validation failed",
    "details": [
      "Email is required",
      "Password must be at least 8 characters"
    ]
  }
}
\`\`\`

## 🧪 Testing

Run the test suite:

\`\`\`bash
# Unit tests
npm run test

# Integration tests  
npm run test:integration

# End-to-end tests
npm run test:e2e

# Test coverage
npm run test:coverage
\`\`\`

## 📦 Deployment

### Environment-specific Builds

\`\`\`bash
# Development
npm run build:dev

# Staging
npm run build:staging

# Production
npm run build:prod
\`\`\`

### Production Deployment

1. **Environment Variables**
   \`\`\`bash
   NODE_ENV=production
   DATABASE_URL=mongodb://production-db:27017/app
   REDIS_URL=redis://production-redis:6379
   JWT_SECRET=your-production-jwt-secret
   \`\`\`

2. **Build and Deploy**
   \`\`\`bash
   npm run build:prod
   npm start
   \`\`\`

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch (\`git checkout -b feature/amazing-feature\`)
3. Commit your changes (\`git commit -m 'Add some amazing feature'\`)
4. Push to the branch (\`git push origin feature/amazing-feature\`)
5. Open a Pull Request

### Development Guidelines

- Follow the existing code style
- Write tests for new features
- Update documentation
- Ensure all tests pass

## 📖 Additional Resources

- [API Documentation](docs/api.md)
- [Architecture Guide](docs/architecture.md)
- [Deployment Guide](docs/deployment.md)
- [Contributing Guidelines](CONTRIBUTING.md)

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [Express.js](https://expressjs.com/) - Web framework
- [MongoDB](https://www.mongodb.com/) - Database
- [React](https://reactjs.org/) - Frontend library
- [Tailwind CSS](https://tailwindcss.com/) - CSS framework

## 📞 Support

If you have any questions or need help:

- 📧 Email: support@{{domain}}
- 💬 Discord: [Join our server](https://discord.gg/...)
- 📖 Documentation: [docs.{{domain}}](https://docs.{{domain}})`,
  }
};
