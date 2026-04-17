# TDD Patterns — NestJS 11 / TypeScript

## Test Structure (Jest)

```typescript
// Unit test — isolated service
describe('UserService', () => {
  let service: UserService;
  let repository: jest.Mocked<UserRepository>;

  beforeEach(async () => {
    const module: TestingModule = await Test.createTestingModule({
      providers: [
        UserService,
        {
          provide: UserRepository,
          useValue: {
            findByEmail: jest.fn(),
            save: jest.fn(),
          },
        },
      ],
    }).compile();

    service = module.get<UserService>(UserService);
    repository = module.get(UserRepository);
  });

  describe('createUser', () => {
    it('should throw ConflictException when email already exists', async () => {
      // ARRANGE
      repository.findByEmail.mockResolvedValue(existingUser());

      // ACT + ASSERT
      await expect(service.createUser(newUserDto())).rejects.toThrow(
        ConflictException,
      );
    });
  });
});
```

## Integration Test (supertest + e2e)

```typescript
// test/users.e2e-spec.ts
describe('Users (e2e)', () => {
  let app: INestApplication;

  beforeAll(async () => {
    const moduleFixture = await Test.createTestingModule({
      imports: [AppModule],
    }).compile();

    app = moduleFixture.createNestApplication();
    await app.init();
  });

  afterAll(() => app.close());

  it('POST /users — valid request -> 201', () => {
    return request(app.getHttpServer())
      .post('/users')
      .send(validCreateUserDto())
      .expect(201)
      .expect((res) => {
        expect(res.body.id).toBeDefined();
        expect(res.body.email).toBe('test@example.com');
      });
  });
});
```

## Controller Test

```typescript
describe('UserController', () => {
  let controller: UserController;
  let service: jest.Mocked<UserService>;

  beforeEach(async () => {
    const module = await Test.createTestingModule({
      controllers: [UserController],
      providers: [
        {
          provide: UserService,
          useValue: { findById: jest.fn() },
        },
      ],
    }).compile();

    controller = module.get<UserController>(UserController);
    service = module.get(UserService);
  });

  it('should return user when found', async () => {
    service.findById.mockResolvedValue(mockUser());
    const result = await controller.findOne('user-id');
    expect(result).toMatchObject({ id: 'user-id' });
  });
});
```

## Mocking Rules

- `jest.fn()` for method mocks on injected dependencies
- `jest.spyOn()` for partial mocks on real instances
- Always `mockResolvedValue` for async (not `mockReturnValue`)
- `mockRejectedValue(new SomeException())` for error paths
- Reset mocks between tests: `jest.clearAllMocks()` in `afterEach`

## RED-GREEN Example

```bash
# RED
npx jest --testPathPattern=user.service.spec --testNamePattern="throw ConflictException"
# Expected: FAIL

# GREEN — implement logic
npx jest --testPathPattern=user.service.spec --testNamePattern="throw ConflictException"
# Expected: PASS

# Full suite
npx jest
```
