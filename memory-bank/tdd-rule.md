# Test-Driven Development (TDD) Rule for Lingible Backend

## 🎯 **RULE: All Backend Changes Must Follow TDD**

**Effective Date:** 2024-12-19
**Scope:** All backend code changes, modifications, and new features
**Enforcement:** Mandatory for all development work

## 📋 **TDD Workflow (Red-Green-Refactor)**

### **1. RED Phase - Write Failing Tests First**
- **Before writing any production code**, write tests that describe the desired behavior
- Tests must fail initially (Red phase)
- Tests should cover:
  - Happy path scenarios
  - Edge cases and error conditions
  - Input validation
  - Business logic rules
  - Error handling

### **2. GREEN Phase - Write Minimal Code**
- Write the **minimum amount of code** to make tests pass
- Focus on functionality, not optimization
- Code should be simple and straightforward
- No premature optimization or refactoring

### **3. REFACTOR Phase - Clean Up Code**
- Once tests pass, refactor the code for:
  - Readability and maintainability
  - Performance optimization
  - Code organization
  - Removing duplication
- **Tests must continue to pass** after refactoring

## 🧪 **Test Requirements**

### **Test Categories Required:**
1. **Unit Tests** - Test individual functions/methods in isolation
2. **Integration Tests** - Test component interactions
3. **Model Tests** - Test Pydantic model validation and behavior
4. **Service Tests** - Test business logic in service layer
5. **Repository Tests** - Test data access layer
6. **Handler Tests** - Test Lambda function handlers
7. **Utility Tests** - Test helper functions and utilities

### **Test Coverage Standards:**
- **Minimum 90% code coverage** for new code
- **100% coverage** for critical business logic
- **All public methods** must have tests
- **Error paths** must be tested
- **Edge cases** must be covered

### **Test Quality Standards:**
- Tests must be **readable and descriptive**
- Use **AAA pattern** (Arrange, Act, Assert)
- **Mock external dependencies** (AWS services, databases)
- **Test one thing per test method**
- **Use meaningful test names** that describe the scenario
- **Avoid test interdependence**

## 🔧 **Implementation Guidelines**

### **For New Features:**
1. **Write tests first** that describe the feature behavior
2. **Implement the feature** to make tests pass
3. **Refactor** for clean, maintainable code
4. **Ensure all tests pass** before committing

### **For Bug Fixes:**
1. **Write a test** that reproduces the bug (should fail)
2. **Fix the bug** to make the test pass
3. **Add additional tests** to prevent regression
4. **Refactor** if needed while keeping tests green

### **For Code Refactoring:**
1. **Ensure existing tests pass** before starting
2. **Refactor code** incrementally
3. **Run tests after each change**
4. **Add new tests** for any new behavior introduced

## 📁 **File Organization**

### **Test File Structure:**
```
tests/
├── test_models.py          # Model validation tests
├── test_services.py        # Service layer tests
├── test_repositories.py    # Repository layer tests
├── test_utils.py          # Utility function tests
├── test_handlers.py       # Lambda handler tests
└── conftest.py            # Shared fixtures and configuration
```

### **Test Naming Conventions:**
- Test classes: `Test{ClassName}`
- Test methods: `test_{scenario}_{expected_result}`
- Example: `test_translate_english_to_genz_success`

## 🚀 **Development Workflow**

### **Before Starting Development:**
1. **Understand the requirement** completely
2. **Identify test scenarios** and edge cases
3. **Plan the test structure** and coverage

### **During Development:**
1. **Write failing test** (Red)
2. **Implement minimal code** (Green)
3. **Refactor and improve** (Refactor)
4. **Run full test suite** to ensure no regressions
5. **Check coverage** meets standards

### **Before Committing:**
1. **All tests must pass**
2. **Coverage meets minimum standards**
3. **Code follows style guidelines** (black, flake8, mypy)
4. **Tests are well-documented**

## 🛠 **Tools and Commands**

### **Test Execution:**
```bash
# Run all tests
python run_tests.py

# Run specific test file
python -m pytest tests/test_models.py -v

# Run with coverage
python run_tests.py --coverage

# Run only unit tests
python run_tests.py --type unit

# Run fast tests only
python run_tests.py --fast
```

### **Coverage Reporting:**
```bash
# Generate coverage report
python run_tests.py --coverage

# View HTML coverage report
open htmlcov/index.html
```

## 📊 **Quality Metrics**

### **Success Criteria:**
- ✅ All tests pass (0 failures)
- ✅ Coverage ≥ 90% for new code
- ✅ No test interdependence
- ✅ Tests are readable and maintainable
- ✅ Error scenarios are covered
- ✅ Edge cases are tested

### **Failure Criteria:**
- ❌ Tests fail or are missing
- ❌ Coverage below 90%
- ❌ Tests are hard to understand
- ❌ Missing error scenario tests
- ❌ Tests depend on each other

## 🔄 **Continuous Integration**

### **Pre-commit Checks:**
- Run full test suite
- Check coverage requirements
- Run code quality checks (black, flake8, mypy)
- Ensure all tests pass

### **CI/CD Pipeline:**
- Automated test execution on every commit
- Coverage reporting and tracking
- Test result notifications
- Block deployment if tests fail

## 📚 **Best Practices**

### **Test Design:**
- **Test behavior, not implementation**
- **Use descriptive test names**
- **Keep tests simple and focused**
- **Avoid test code duplication**
- **Use appropriate assertions**

### **Mocking Strategy:**
- **Mock external dependencies**
- **Use realistic test data**
- **Avoid over-mocking**
- **Test integration points separately**

### **Test Data:**
- **Use fixtures for common data**
- **Create realistic test scenarios**
- **Avoid hardcoded values**
- **Use factories for complex objects**

## 🎯 **Examples**

### **Example: Adding New Translation Feature**
1. **Write test first:**
   ```python
   def test_translate_with_custom_model_success(self):
       """Test translation with custom model selection."""
       request = TranslationRequest(
           text="Hello world",
           direction=TranslationDirection.ENGLISH_TO_GENZ,
           model="custom-model"
       )

       result = translation_service.translate(request, sample_user)

       assert result.translation_id is not None
       assert result.model_used == "custom-model"
   ```

2. **Implement feature** to make test pass
3. **Add error tests:**
   ```python
   def test_translate_with_invalid_model_raises_error(self):
       """Test translation with invalid model raises error."""
       request = TranslationRequest(
           text="Hello world",
           direction=TranslationDirection.ENGLISH_TO_GENZ,
           model="invalid-model"
       )

       with pytest.raises(ValidationError):
           translation_service.translate(request, sample_user)
   ```

4. **Refactor** for clean code
5. **Ensure all tests pass**

## ⚠️ **Exceptions and Special Cases**

### **Emergency Hotfixes:**
- **Immediate production issues** may require quick fixes
- **Tests must be added within 24 hours**
- **Document the exception** in commit message
- **Create follow-up task** for proper TDD implementation

### **Third-party Dependencies:**
- **External library updates** may not require TDD
- **Integration tests** still required
- **Regression tests** must be added

## 📈 **Continuous Improvement**

### **Regular Reviews:**
- **Weekly test quality reviews**
- **Coverage trend analysis**
- **Test performance monitoring**
- **Refactoring opportunities**

### **Team Training:**
- **TDD workshops** and training
- **Test writing best practices**
- **Mocking strategies**
- **Test design patterns**

---

**This rule is mandatory for all backend development work. Any code changes without proper test coverage will be rejected during code review.**
