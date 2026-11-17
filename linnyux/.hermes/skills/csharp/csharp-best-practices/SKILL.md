---
name: csharp-best-practices
description: Comprehensive C#/.NET development best practices covering async programming, testing frameworks, documentation, and architecture patterns. Use when writing C# code, setting up testing, documenting types, or building .NET applications. Includes all language-specific standards and frameworks.
license: MIT
---

# C# Best Practices Library

Comprehensive C#/.NET development standard including async programming, testing frameworks, documentation, and architectural patterns. These are the patterns used across production systems.

## When to Use

**Triggers:**
- Writing C# code
- Setting up .NET projects
- Configuring testing frameworks (xUnit, NUnit, MSTest, TUnit)
- Documenting types and APIs
- Building async systems
- Creating MCP servers in C#

**Context:**
- All .NET development (NET 6+ through .NET 8+)
- API development and documentation
- Test-driven development in C#
- Async and concurrent programming

---

## Table of Contents

### Language Fundamentals
- [Async Programming](#async-programming) — Best practices for async code
- [XML Documentation](#xml-documentation) — Type and API documentation

### Testing Frameworks
- [xUnit Testing](#xunit-testing) — XUnit 3.x best practices
- [NUnit Testing](#nunit-testing) — NUnit best practices
- [MSTest Testing](#mstest-testing) — MSTest 3.x/4.x patterns
- [TUnit Testing](#tunit-testing) — TUnit testing patterns

### Code Generation
- [C# MCP Server Generator](#c-mcp-server-generator) — Create MCP servers in C#

---

## Async Programming

### When to Use Async/Await

**Use async/await when:**
- I/O-bound operations (file, network, database calls)
- Waiting on other tasks
- API calls, file access, database queries
- Any operation that would block the calling thread

**DO NOT use async for:**
- CPU-bound operations (use `Task.Run()` if needed)
- Simple synchronous code
- When you need to return early in all code paths

### The Async/Await Pattern

**Correct Pattern:**
```csharp
public async Task<string> GetDataAsync()
{
    using var client = new HttpClient();
    client.Timeout = TimeSpan.FromSeconds(30);
    
    return await client.GetStringAsync("https://api.example.com/data");
}
```

**Key Principles:**
1. **Always use async all the way** — Don't block with `.Result` or `.Wait()`
2. **Use ConfigureAwait(false)** in library code (not in UI code)
3. **Pass CancellationToken** through async chains
4. **Avoid async void** — Only use for event handlers
5. **Use `when` for exception handling in tasks**

### CancellationToken Best Practices

**Propagate cancellation through async chains:**
```csharp
public async Task<string> GetDataAsync(CancellationToken cancellationToken = default)
{
    using var client = new HttpClient();
    var response = await client.GetStringAsync(
        "https://api.example.com/data", 
        cancellationToken
    );
    return response;
}
```

**Register callbacks for cleanup:**
```csharp
var cts = new CancellationTokenSource();
cts.Token.Register(() => Cleanup());
```

### Common Async Anti-Patterns

**DON'T: Blocking on async code**
```csharp
// BAD - Can cause deadlocks
var result = GetDataAsync().Result;
var result = GetDataAsync().Wait();
```

**DO: Use async/await everywhere**
```csharp
// GOOD
var result = await GetDataAsync();
```

**DON'T: Async void methods**
```csharp
// BAD - No error handling
private async void LoadData() { }

// GOOD
private async Task LoadDataAsync() { }
```

**DON'T: Task.Run() for I/O**
```csharp
// BAD - Unnecessary thread pool usage
var result = await Task.Run(() => File.ReadAllText(path));

// GOOD
var result = await File.ReadAllTextAsync(path);
```

---

## XML Documentation

### Type Documentation

**Class Documentation:**
```csharp
/// <summary>
/// Provides data access for user accounts.
/// </summary>
/// <remarks>
/// This class handles CRUD operations for user data.
/// </remarks>
public class UserService
{
}
```

**Method Documentation:**
```csharp
/// <summary>
/// Retrieves a user by their unique identifier.
/// </summary>
/// <param name="userId">The unique user identifier.</param>
/// <returns>The user object if found; otherwise, null.</returns>
/// <exception cref="ArgumentNullException">
/// Thrown when <paramref name="userId"/> is null or empty.
/// </exception>
/// <exception cref="KeyNotFoundException">
/// Thrown when user with specified ID is not found.
/// </exception>
public async Task<User?> GetUserByIdAsync(string userId)
{
}
```

**Property Documentation:**
```csharp
/// <summary>
/// Gets or sets the user's display name.
/// </summary>
public string DisplayName { get; set; } = string.Empty;
```

### XML Documentation Tags

**Required tags:**
- `<summary>` — One-line description of the type/member
- `<param name="...">` — Parameter description
- `<returns>` — Return value description (for non-void methods)
- `<exception cref="...">` — Exception documentation

**Optional tags:**
- `<remarks>` — Additional notes
- `<example>` — Code example
- `<see cref="..."/>` — Cross-reference to another member
- `<see langword="..."/>` — Link to keyword

### Documentation Best Practices

**Do:**
- Use `<summary>` for all public types and members
- Describe what, not how (implementation details are in code)
- Use `paramref` for parameter names
- Document all exceptions that can be thrown
- Use `<see>` for type references

**Don't:**
- Repeat information that's obvious from the signature
- Document internal/private methods (unless part of public API)
- Use vague language like "does stuff"
- Forget to document return values

---

## xUnit Testing

### Test Structure

**Arrange-Act-Assert Pattern:**
```csharp
[Fact]
public async Task GetUserByIdAsync_WhenUserExists_ReturnsUser()
{
    // Arrange
    var repository = new Mock<IUserRepository>();
    var user = new User { Id = "123", Name = "John" };
    repository.Setup(r => r.GetByIdAsync("123", It.IsAny<CancellationToken>()))
              .ReturnsAsync(user);
    
    var service = new UserService(repository.Object);
    
    // Act
    var result = await service.GetUserByIdAsync("123");
    
    // Assert
    Assert.NotNull(result);
    Assert.Equal("John", result.Name);
}
```

### Data-Driven Testing

**Theory with Inline Data:**
```csharp
[Theory]
[InlineData("valid@example.com", true)]
[InlineData("invalid-email", false)]
[InlineData("", false)]
public void ValidateEmail_WithValidInput_ReturnsExpectedResult(
    string email, 
    bool expected)
{
    var service = new EmailService();
    var result = service.ValidateEmail(email);
    Assert.Equal(expected, result);
}
```

**Theory with Class Data:**
```csharp
public class TaxCalculationTests : IDisposable
{
    public static IEnumerable<object[]> TaxTestData =>
        new List<object[]>
        {
            new object[] { 1000m, 100m },
            new object[] { 5000m, 500m },
            new object[] { 10000m, 1000m },
        };
    
    [Theory]
    [MemberData(nameof(TaxTestData))]
    public void CalculateTax_CorrectAmount(decimal income, decimal expectedTax)
    {
        var calculator = new TaxCalculator();
        var result = calculator.Calculate(income);
        Assert.Equal(expectedTax, result);
    }
}
```

### Mocking Best Practices

**Mock Setup:**
```csharp
_repository.Setup(r => r.GetByIdAsync(It.IsAny<string>(), It.IsAny<CancellationToken>()))
           .ReturnsAsync(new User { Id = "123", Name = "Test" });

// Verify it was called
_repository.Verify(r => r.GetByIdAsync("123", CancellationToken.None), Times.Once);
```

**Avoid Over-Mocking:**
- Only mock dependencies, not collaborators
- Use `Fake` for simple interfaces
- Prefer real objects when possible

### Test Naming Conventions

**Good names include:**
- Method being tested
- Condition/senario
- Expected result

```csharp
[Fact]
public async Task AddItemToCart_WhenItemDoesNotExist_ReturnsSuccess()
{
}

[Fact]
public async Task AddItemToCart_WhenItemAlreadyExists_IncrementsQuantity()
{
}
```

---

## NUnit Testing

### Test Attributes

**Available attributes:**
- `[Test]` — Test method
- `[TestCase]` — Data-driven test
- `[OneTimeSetUp]` / `[OneTimeTearDown]` — Setup for all tests in class
- `[SetUp]` / `[TearDown]` — Setup/teardown per test
- `[Description]` — Test description

### Test Structure

**Basic Test:**
```csharp
[TestFixture]
public class UserServiceTests
{
    private UserService _service;
    
    [SetUp]
    public void Setup()
    {
        _service = new UserService();
    }
    
    [Test]
    public void GetUser_WhenExists_ReturnsUser()
    {
        // Arrange
        var user = new User { Id = "123", Name = "John" };
        
        // Act
        var result = _service.GetUser("123");
        
        // Assert
        Assert.That(result, Is.Not.Null);
    }
}
```

### Assertions

**NUnit Assertions:**
```csharp
// Equality
Assert.That(result, Is.EqualTo(expected));

// Null check
Assert.IsNull(result);

// Exception expectation
Assert.Throws<InvalidOperationException>(
    () => service.DoSomethingInvalid()
);

// Collection checks
Assert.That(collection, Has.Count.EqualTo(5));
Assert.That(collection, Does.Contain(item));
```

---

## MSTest Testing

### Test Attributes

**Available attributes:**
- `[TestClass]` — Test class
- `[TestMethod]` — Test method
- `[DataTestMethod]` — Data-driven test
- `[DataRow]` — Test data for data-driven tests
- `[TestInitialize]` / `[TestCleanup]` — Per-test setup/teardown
- `[AssemblyInitialize]` / `[AssemblyCleanup]` — Assembly-level setup/teardown

### Test Structure

**Basic Test:**
```csharp
[TestClass]
public class UserServiceTests
{
    private UserService _service;
    
    [TestInitialize]
    public void TestInitialize()
    {
        _service = new UserService();
    }
    
    [TestMethod]
    public async Task GetUser_WhenExists_ReturnsUser()
    {
        // Arrange
        var user = new User { Id = "123", Name = "John" };
        
        // Act
        var result = await _service.GetUserAsync("123");
        
        // Assert
        Assert.IsNotNull(result);
        Assert.AreEqual("John", result.Name);
    }
}
```

### Data-Driven Tests

**DataRow examples:**
```csharp
[DataTestMethod]
[DataRow("valid@example.com", true)]
[DataRow("invalid", false)]
[DataRow("", false)]
public void ValidateEmail_WithValidInput_ReturnsExpectedResult(
    string email, 
    bool expected)
{
    var service = new EmailService();
    var result = service.ValidateEmail(email);
    Assert.AreEqual(expected, result);
}
```

### Assertions

**MSTest Assertions:**
```csharp
Assert.AreEqual(expected, actual);
Assert.AreNotEqual(expected, actual);
Assert.IsNotNull(result);
Assert.IsNull(result);
Assert.IsTrue(condition);
Assert.IsFalse(condition);

// Exceptions
Assert.ThrowsException<InvalidOperationException>(
    () => service.DoSomethingInvalid()
);

// Async exceptions
await Assert.ThrowsExceptionAsync<InvalidOperationException>(
    async () => await service.DoSomethingInvalidAsync()
);
```

---

## TUnit Testing

### Test Attributes

TUnit uses modern TDD patterns with minimal ceremony:

```csharp
[Test]
public void BasicTest()
{
    // Arrange
    // Act
    // Assert
}
```

### Async Tests

```csharp
[Test]
public async Task AsyncTest()
{
    var result = await DoWorkAsync();
    Assert.AreEqual(expected, result);
}
```

### Parallel Execution

```csharp
[Test(ExecutionBehavior = ExecutionBehavior.Parallel)]
public void ParallelTest()
{
    // This test can run in parallel with others
}
```

---

## C# MCP Server Generator

**Purpose:** Generate complete MCP server projects in C# with tools, prompts, and resources.

### What Gets Generated

**Project Structure:**
- MCP server implementation
- Tool definitions and handlers
- Prompt templates
- Resource providers
- Configuration files
- Tests for all components

**Key Features:**
- Auto-discovery of tools and resources
- Proper error handling
- Serialization/deserialization
- Logging and diagnostics
- Documentation generation

### Best Practices

**Tool Design:**
- Clear, descriptive names
- Comprehensive input validation
- Detailed parameter documentation
- Consistent return types

**Error Handling:**
- Return meaningful error messages
- Use structured exceptions
- Log errors appropriately

**Testing:**
- Unit tests for each tool
- Integration tests for workflows
- Error scenario coverage

---

## Common Mistakes in C#/.NET Development

### Async Anti-Patterns

**DON'T: Blocking on async code**
```csharp
// BAD - Deadlock risk
var result = GetDataAsync().Result;

// GOOD
var result = await GetDataAsync();
```

**DON'T: Task.Run() for I/O**
```csharp
// BAD
var result = await Task.Run(() => ReadFile(path));

// GOOD
var result = await File.ReadAllTextAsync(path);
```

### Testing Mistakes

**DON'T: Ignore exceptions**
```csharp
// BAD - Exceptions swallowed
try {
    await DoSomething();
} catch {
    // Ignored
}

// GOOD
try {
    await DoSomething();
} catch (Exception ex) {
    Log.Error(ex);
    throw;
}
```

**DON'T: Over-mock**
```csharp
// BAD - Mocking the repository even when we can use fake
var mock = new Mock<IRepository>();

// GOOD - Use fake for simple interface implementations
var fake = new InMemoryRepository();
```

### Documentation Mistakes

**DON'T: Skip parameter names**
```csharp
/// <summary>
/// Gets user.
/// </summary>
/// <param name="id">User id</param> // Good
public User GetUser(string id) {}

// Bad - Missing parameter name
public User GetUser(string userId) {} // userId not in summary
```

**DON'T: Document implementation details**

Document what, not how. Implementation details are in the code.

---

## Best Practices by Scenario

### Creating a Service Class

```csharp
/// <summary>
/// Provides user account management functionality.
/// </summary>
public class UserService : IUserService, IDisposable
{
    private readonly IUserRepository _repository;
    private readonly ILogger<UserService> _logger;
    private bool _disposed;

    /// <summary>
    /// Initializes a new instance of the <see cref="UserService"/> class.
    /// </summary>
    public UserService(
        IUserRepository repository,
        ILogger<UserService> logger)
    {
        _repository = repository ?? throw new ArgumentNullException(nameof(repository));
        _logger = logger ?? throw new ArgumentNullException(nameof(logger));
    }

    /// <summary>
    /// Retrieves a user by their unique identifier.
    /// </summary>
    /// <param name="userId">The unique user identifier.</param>
    /// <param name="cancellationToken">Cancellation token.</param>
    /// <returns>The user object if found.</returns>
    /// <exception cref="ArgumentException">
    /// Thrown when userId is null or empty.
    /// </exception>
    public async Task<User?> GetUserByIdAsync(
        string userId,
        CancellationToken cancellationToken = default)
    {
        if (string.IsNullOrEmpty(userId))
            throw new ArgumentException("User ID cannot be null or empty", nameof(userId));

        _logger.LogInformation("Getting user by ID: {UserId}", userId);
        
        return await _repository.GetByIdAsync(userId, cancellationToken);
    }

    public void Dispose()
    {
        if (_disposed) return;
        
        _repository.Dispose();
        _disposed = true;
        GC.SuppressFinalize(this);
    }
}
```

### Writing Unit Tests

```csharp
[TestClass]
public class UserServiceTests
{
    private UserService _service;
    private Mock<IUserRepository> _repositoryMock;
    
    [TestInitialize]
    public void TestInitialize()
    {
        _repositoryMock = new Mock<IUserRepository>();
        _service = new UserService(_repositoryMock.Object, Mock.Of<ILogger<UserService>>());
    }
    
    [TestMethod]
    public async Task GetUserByIdAsync_WhenUserIdExists_ReturnsUser()
    {
        // Arrange
        var user = new User { Id = "123", Name = "John" };
        _repositoryMock.Setup(r => r.GetByIdAsync("123", It.IsAny<CancellationToken>()))
                      .ReturnsAsync(user);
        
        // Act
        var result = await _service.GetUserByIdAsync("123");
        
        // Assert
        Assert.IsNotNull(result);
        Assert.AreEqual("John", result.Name);
    }
    
    [TestMethod]
    [ExpectedException(typeof(ArgumentException))]
    public async Task GetUserByIdAsync_WhenUserIdEmpty_ThrowsArgumentException()
    {
        await _service.GetUserByIdAsync("");
    }
}
```

---

## Quick Reference

**Async Pattern:**
- Use `async Task<T>` for methods returning values
- Use `async Task` for void-returning async methods
- Always pass `CancellationToken`
- Never block with `.Result` or `.Wait()`
- Use `ConfigureAwait(false)` in libraries

**Documentation:**
- Document all public types and members
- Use `<summary>`, `<param>`, `<returns>`, `<exception>`
- Describe what, not how
- Document all throw exceptions
- Use `<see>` for cross-references

**Testing:**
- Use Arrange-Act-Assert pattern
- Name tests: Method_Scenario_ExpectedResult
- Mock dependencies, not collaborators
- Test error conditions
- Use data-driven tests for common patterns

**MCP Servers:**
- Clear tool names
- Comprehensive parameter docs
- Structured error handling
- Complete test coverage

---

*Comprehensive C#/.NET best practices library consolidating async programming, testing frameworks (xUnit, NUnit, MSTest, TUnit), XML documentation, and MCP server generation patterns. All C# language and framework skills merged into one class-level reference for production .NET development.*