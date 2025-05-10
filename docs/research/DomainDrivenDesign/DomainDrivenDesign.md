# Building with purpose: Domain-Driven Design for Python 3.12

## Bottom line up front

Domain-Driven Design (DDD) brings clarity to complex software projects by focusing on the business domain rather than technical implementations. For Python 3.12 developers on Linux, DDD offers a structured way to build maintainable systems that accurately reflect business needs. This guide provides both theoretical understanding and practical implementation details specifically optimized for Python 3.12, including code examples and templates that leverage Python's latest features like improved type annotations and dataclass enhancements.

## Part A: Understanding Domain-Driven Design foundations

### Why domain-driven design matters

Domain-Driven Design emerged from Eric Evans' experiences working on complex enterprise applications, documented in his 2003 book "Domain-Driven Design: Tackling Complexity in the Heart of Software." At its core, DDD provides a set of principles and practices for tackling complexity by:

1. Building a rich domain model that directly represents business concepts
2. Creating a shared language between technical and domain experts
3. Focusing on the core domain where business value lies
4. Establishing clear boundaries within your software

DDD shines in complex domains where traditional CRUD approaches fail to capture essential business rules and relationships. The methodology emphasizes continuous collaboration between domain experts and developers to build software that embodies domain knowledge rather than merely manipulating data.

### Core concepts that power DDD

#### The ubiquitous language

The ubiquitous language forms the foundation of successful DDD implementations. It's a common, shared vocabulary that domain experts and developers collaboratively develop and use consistently throughout all aspects of a project—from discussions to documentation to code.

This shared language:
- Creates a bridge between technical and business stakeholders
- Reduces misunderstandings by eliminating translation layers
- Enables code to directly reflect domain concepts
- Evolves as understanding of the domain deepens

For example, in an e-commerce domain, terms like "shopping cart," "backorder," and "return policy" would have precise, agreed-upon meanings reflected directly in class names, attributes, and methods.

#### Bounded contexts: defining model boundaries

A bounded context establishes the boundaries where specific domain models apply. This concept addresses the challenge of working with large, complex domains by dividing them into manageable subsystems where terms from the ubiquitous language have consistent meaning.

Key aspects include:
- Defining where a particular model is valid and applicable
- Establishing boundaries where domain terms have clear meanings
- Managing complexity by dividing large domains into coherent subdomains
- Allowing different models to coexist without contaminating each other

For example, a product in the "Inventory Management" context might focus on stock levels and warehouse locations, while in the "Customer Experience" context, it emphasizes descriptions, reviews, and recommendations.

#### Building blocks of the domain model

DDD defines several tactical patterns for implementing domain models:

**Entities vs Value Objects**
- **Entities** have distinct identities that persist across changes to their attributes (Example: Customer, Order)
- **Value Objects** are defined solely by their attributes, are immutable, and lack identity (Example: Money, Address)

**Aggregates and Aggregate Roots**
- An aggregate is a cluster of domain objects that can be treated as a single unit
- Each aggregate has a root entity (the aggregate root) that controls access
- Aggregates define consistency boundaries within the domain
- Example: An Order (root) containing OrderLine items as an aggregate

**Repositories**
- Provide an abstraction layer for accessing aggregates
- Present a collection-like interface for finding and retrieving domain objects
- Encapsulate storage and retrieval details
- Operate at the aggregate level

**Domain Services**
- Contain domain logic that doesn't naturally fit within entities or value objects
- Implement operations involving multiple domain objects
- Stateless operations named after activities rather than things

**Domain Events**
- Represent significant occurrences within the domain
- Immutable records of something that happened
- Enable event-driven architectures and communication between bounded contexts
- Named with past-tense verbs (OrderPlaced, PaymentReceived)

**Factories**
- Encapsulate the logic for creating complex domain objects
- Ensure created objects are valid and consistent
- Hide complexity of object creation
- Allow for clear separation between creation and usage

### Strategic vs tactical design

Domain-Driven Design separates concerns into two distinct aspects:

**Strategic Design**
- Focuses on the big picture—understanding the problem domain
- Analyzes the business domain and identifies subdomains
- Divides the system into bounded contexts
- Establishes the ubiquitous language
- Creates context maps showing relationships between contexts

**Tactical Design**
- Focuses on implementation details within a bounded context
- Implements entities, value objects, and aggregates
- Designs repositories and factories
- Defines domain services and handles domain events

### DDD's relationship with modern architecture

DDD works seamlessly with several architectural patterns:

**Hexagonal Architecture** (Ports and Adapters)
- Places the domain model at the center (inside the hexagon)
- Defines ports (interfaces) for interaction with external systems
- Uses adapters to implement these ports for specific technologies
- Preserves the purity of the domain model

**Clean Architecture**
- Organizes code in concentric circles with dependencies pointing inward
- Places entities and business rules at the center
- DDD's domain model fits naturally in the innermost circles

**Microservices**
- Bounded contexts provide a principled way to define microservice boundaries
- Each microservice can have its own domain model
- Context mapping patterns define interaction between services

**Event Sourcing and CQRS**
- Domain events provide the foundation for event sourcing
- Aggregates define consistency boundaries for updates
- Read models can be optimized without compromising the domain model

## Part B: Implementing DDD in Python 3.12

### Step-by-step implementation guide

#### 1. Understanding the domain

Begin by collaborating with domain experts to:
- Identify core business concepts and processes
- Develop a glossary of domain terms (ubiquitous language)
- Map out business workflows and rules
- Identify the core domain and supporting subdomains

Techniques like Event Storming can be particularly valuable here, bringing together domain experts and developers to map out business processes using sticky notes representing domain events, commands, and other elements.

#### 2. Defining bounded contexts

Identify different contexts in your application by:
- Recognizing where terminology takes on different meanings
- Finding natural divisions in the business domain
- Determining responsibility boundaries
- Considering team structures and system components

For each bounded context, document:
- Its purpose and responsibility
- Key domain concepts and their definitions
- Relationships with other contexts
- Primary actors and use cases

#### 3. Modeling the domain

Start modeling by identifying:
- Entities with unique identities (e.g., User, Order)
- Value objects defined by attributes (e.g., Address, Money)
- Aggregates and their boundaries
- Domain services for operations spanning multiple entities
- Domain events representing significant occurrences

Python 3.12 provides excellent tools for this modeling with:
- Dataclasses for entities and value objects
- Type annotations for clearer domain modeling
- Improved pattern matching for working with domain objects
- Performance optimizations for frequently used domain objects

#### 4. Implementing the core domain model

With Python 3.12, implement your model starting with:

**Value objects** as immutable dataclasses:

```python
from dataclasses import dataclass
from typing import ClassVar
from decimal import Decimal
import re

@dataclass(frozen=True)
class Email:
    """Email value object with validation"""
    value: str
    
    # Class-level constants
    _PATTERN: ClassVar[str] = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    
    def __post_init__(self):
        """Validate email on initialization"""
        if not re.match(self._PATTERN, self.value):
            raise ValueError(f"Invalid email format: {self.value}")
        
        # In Python 3.12, use object.__setattr__ to modify frozen dataclass attributes
        object.__setattr__(self, "value", self.value.lower())

@dataclass(frozen=True)
class Money:
    """Money value object"""
    amount: Decimal
    currency: str
    
    def __post_init__(self):
        """Validate money parameters"""
        if self.amount < 0:
            raise ValueError("Amount cannot be negative")
        if len(self.currency) != 3:
            raise ValueError("Currency must be a 3-letter code")
    
    def __add__(self, other):
        """Return a new Money object with the sum of amounts"""
        if not isinstance(other, Money):
            return NotImplemented
        if self.currency != other.currency:
            raise ValueError("Cannot add different currencies")
        return Money(self.amount + other.amount, self.currency)
```

**Entities** with identity:

```python
from dataclasses import dataclass, field
from typing import Optional
from uuid import UUID, uuid4
from datetime import datetime

class Entity:
    """Base class for all entities"""
    id: UUID
    
    def __eq__(self, other):
        if not isinstance(other, Entity):
            return False
        return self.id == other.id
    
    def __hash__(self):
        return hash(self.id)

@dataclass(eq=False)  # Inherit equality from Entity
class User(Entity):
    """User entity"""
    id: UUID = field(default_factory=uuid4)
    email: Email
    name: str
    created_at: datetime = field(default_factory=datetime.now)
    
    @classmethod
    def create(cls, email: str, name: str) -> 'User':
        """Factory method to create a new user"""
        return cls(
            id=uuid4(),
            email=Email(email),
            name=name
        )
```

**Aggregates** that maintain consistency boundaries:

```python
from typing import List

@dataclass
class AggregateRoot(Entity):
    """Base class for aggregate roots"""
    _events: List = field(default_factory=list, init=False, repr=False)
    
    def add_event(self, event) -> None:
        """Add a domain event"""
        self._events.append(event)
    
    @property
    def events(self) -> List:
        """Get all pending domain events"""
        return self._events.copy()
    
    def clear_events(self) -> None:
        """Clear all pending domain events"""
        self._events.clear()

@dataclass
class Order(AggregateRoot):
    """Order aggregate root"""
    id: UUID = field(default_factory=uuid4)
    customer_id: UUID
    items: List['OrderItem'] = field(default_factory=list)
    status: str = "new"
    
    def add_item(self, product_id: UUID, quantity: int, price: Money) -> None:
        """Add an item to the order"""
        item = OrderItem(
            product_id=product_id,
            quantity=quantity,
            price=price
        )
        self.items.append(item)
        self.add_event(OrderItemAdded(order_id=self.id, item=item))
    
    def place(self) -> None:
        """Place the order"""
        if not self.items:
            raise ValueError("Cannot place an empty order")
        
        self.status = "placed"
        self.add_event(OrderPlaced(order_id=self.id))
```

#### 5. Implementing repositories

Repositories provide an abstraction for persistence, allowing your domain model to remain independent of storage concerns:

```python
from abc import ABC, abstractmethod
from typing import List, Optional, Protocol

# Domain layer - Repository interface
class OrderRepository(Protocol):
    """Repository interface for Order aggregates"""
    def save(self, order: Order) -> None:
        """Save an order"""
        ...
    
    def find_by_id(self, order_id: UUID) -> Optional[Order]:
        """Find an order by ID"""
        ...
    
    def find_by_customer_id(self, customer_id: UUID) -> List[Order]:
        """Find all orders for a customer"""
        ...

# Infrastructure layer - Implementation with SQLAlchemy
from sqlalchemy.orm import Session

class SQLAlchemyOrderRepository:
    """SQLAlchemy implementation of OrderRepository"""
    
    def __init__(self, session: Session):
        self.session = session
    
    def save(self, order: Order) -> None:
        # Convert domain objects to ORM models
        order_model = OrderModel.from_entity(order)
        self.session.add(order_model)
        
        # Process domain events
        for event in order.events:
            # Handle or publish events
            event_bus.publish(event)
        
        # Clear events after handling
        order.clear_events()
        
        self.session.commit()
```

#### 6. Domain events and messaging

Domain events enable loose coupling between components:

```python
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

@dataclass(frozen=True)
class DomainEvent:
    """Base class for all domain events"""
    event_id: UUID = field(default_factory=uuid4)
    occurred_on: datetime = field(default_factory=datetime.now)

@dataclass(frozen=True)
class OrderPlaced(DomainEvent):
    """Event raised when an order is placed"""
    order_id: UUID

@dataclass(frozen=True)
class OrderItemAdded(DomainEvent):
    """Event raised when an item is added to an order"""
    order_id: UUID
    item: Any

# Message bus for handling domain events
class MessageBus:
    """Simple implementation of a message bus"""
    
    def __init__(self):
        self.handlers = {}
    
    def register(self, event_type, handler):
        """Register a handler for an event type"""
        if event_type not in self.handlers:
            self.handlers[event_type] = []
        self.handlers[event_type].append(handler)
    
    def publish(self, event: DomainEvent) -> None:
        """Publish an event to all registered handlers"""
        event_type = type(event)
        if event_type in self.handlers:
            for handler in self.handlers[event_type]:
                handler.handle(event)
```

#### 7. Application services

Application services orchestrate domain objects to fulfill use cases:

```python
class OrderService:
    """Application service for order management"""
    
    def __init__(self, order_repository: OrderRepository, payment_service: PaymentService):
        self.order_repository = order_repository
        self.payment_service = payment_service
    
    def place_order(self, customer_id: UUID, items: List[dict]) -> UUID:
        """Place a new order"""
        # Create order aggregate
        order = Order(customer_id=customer_id)
        
        # Add items
        for item in items:
            order.add_item(
                product_id=item["product_id"],
                quantity=item["quantity"],
                price=Money(
                    amount=Decimal(item["price_amount"]),
                    currency=item["price_currency"]
                )
            )
        
        # Place the order
        order.place()
        
        # Save the order
        self.order_repository.save(order)
        
        return order.id
```

#### 8. Bounded context integration

For integrating between bounded contexts, implement anti-corruption layers:

```python
class LegacyOrderSystemAdapter:
    """Adapter for the legacy order system"""
    
    def __init__(self, legacy_client):
        self.legacy_client = legacy_client
    
    def get_order(self, legacy_order_number: str) -> Order:
        """Get an order from the legacy system and convert it to a domain model"""
        # Fetch from legacy system
        legacy_data = self.legacy_client.get_order(legacy_order_number)
        
        # Map status codes
        status_map = {
            "PROC": "processing",
            "SHIP": "shipped",
            "CANC": "cancelled"
        }
        
        # Create domain order
        order = Order(
            customer_id=self._map_customer_id(legacy_data["custId"]),
            status=status_map.get(legacy_data["status"], "unknown")
        )
        
        # Add items
        for item_data in legacy_data["items"]:
            order.add_item(
                product_id=self._map_product_id(item_data["itemNo"]),
                quantity=item_data["qty"],
                price=Money(Decimal(item_data["price"]), "USD")
            )
        
        return order
```

### DDD project structure in Python

A well-organized Python DDD project typically follows this structure:

```
my_project/
├── domain/             # Core domain logic
│   ├── model/          # Domain model (entities, value objects)
│   │   ├── user.py
│   │   ├── order.py
│   │   └── value_objects.py
│   ├── services/       # Domain services
│   ├── repositories/   # Repository interfaces
│   └── events/         # Domain event definitions
├── application/        # Application services and use cases
│   ├── services/       # Orchestrate domain objects for use cases
│   ├── commands/       # Command handlers (for CQRS)
│   └── queries/        # Query handlers (for CQRS)
├── infrastructure/     # Technical implementations
│   ├── repositories/   # Repository implementations
│   ├── persistence/    # ORM and database code
│   └── messaging/      # Event bus and message handling
├── interfaces/         # User interfaces
│   ├── api/            # API endpoints
│   ├── cli/            # Command line interface
│   └── web/            # Web interface
└── main.py             # Application entry point
```

This structure follows the dependency rule where inner layers (domain) know nothing about outer layers, while outer layers depend on inner layers.

### Python 3.12 features for enhanced DDD

Python 3.12 introduces several features that enhance DDD implementation:

**Type parameter syntax** simplifies generic type annotations:

```python
# Before Python 3.12
T = TypeVar('T')
class Repository(Protocol[T]):
    def save(self, entity: T) -> None: ...
    def find_by_id(self, id: UUID) -> Optional[T]: ...

# With Python 3.12
class Repository[T]:
    def save(self, entity: T) -> None: ...
    def find_by_id(self, id: UUID) -> Optional[T]: ...
```

**Enhanced pattern matching** for domain objects:

```python
def handle_event(event: DomainEvent) -> None:
    match event:
        case OrderPlaced(order_id=order_id):
            send_order_confirmation(order_id)
        case OrderItemAdded(order_id=order_id, item=item):
            update_inventory(item.product_id, item.quantity)
        case PaymentProcessed(status="completed"):
            mark_order_as_paid(event.order_id)
```

**Performance improvements for dataclasses** with faster instantiation and attribute access, especially with `slots=True`:

```python
@dataclass(frozen=True, slots=True)
class Address:
    street: str
    city: str
    state: str
    zip_code: str
    country: str
```

**Better error messages** for domain model debugging, with more specific information about what went wrong.

## Part C: Templates and patterns for Python DDD

### Value objects template

```python
from dataclasses import dataclass
from decimal import Decimal
import re
from typing import ClassVar

@dataclass(frozen=True, slots=True)  # Using slots=True for performance in Python 3.12
class Email:
    value: str
    
    # Class-level regex pattern
    _PATTERN: ClassVar[str] = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    
    def __post_init__(self):
        if not isinstance(self.value, str):
            raise ValueError("Email must be a string")
        if not re.match(self._PATTERN, self.value):
            raise ValueError(f"Invalid email format: {self.value}")
        
        # Make value lowercase
        object.__setattr__(self, "value", self.value.lower())

@dataclass(frozen=True, slots=True)
class Money:
    amount: Decimal
    currency: str
    
    def __post_init__(self):
        if not isinstance(self.amount, Decimal):
            object.__setattr__(self, "amount", Decimal(str(self.amount)))
        
        if self.amount < 0:
            raise ValueError("Amount cannot be negative")
        if not isinstance(self.currency, str) or len(self.currency) != 3:
            raise ValueError("Currency must be a 3-letter code")
    
    def __add__(self, other):
        if not isinstance(other, Money):
            return NotImplemented
        if self.currency != other.currency:
            raise ValueError("Cannot add money with different currencies")
        return Money(self.amount + other.amount, self.currency)
    
    def __sub__(self, other):
        if not isinstance(other, Money):
            return NotImplemented
        if self.currency != other.currency:
            raise ValueError("Cannot subtract money with different currencies")
        return Money(self.amount - other.amount, self.currency)
    
    def __mul__(self, multiplier):
        if not isinstance(multiplier, (int, float, Decimal)):
            return NotImplemented
        return Money(self.amount * Decimal(str(multiplier)), self.currency)
```

### Entities template

```python
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

class Entity:
    """Base class for all entities"""
    id: UUID
    
    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        return self.id == other.id
    
    def __hash__(self):
        return hash(self.id)

@dataclass(eq=False)  # Use Entity's equality method
class Product(Entity):
    id: UUID = field(default_factory=uuid4)
    name: str
    description: str
    price: Money
    available: bool = True
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None
    
    def update_price(self, new_price: Money) -> None:
        """Update the product price"""
        if new_price.currency != self.price.currency:
            raise ValueError(f"New price currency {new_price.currency} doesn't match existing currency {self.price.currency}")
        
        self.price = new_price
        self.updated_at = datetime.now()
    
    def make_unavailable(self) -> None:
        """Mark the product as unavailable"""
        self.available = False
        self.updated_at = datetime.now()
```

### Aggregate root template

```python
from dataclasses import dataclass, field
from typing import List, Optional
from uuid import UUID, uuid4

@dataclass
class AggregateRoot(Entity):
    """Base class for aggregate roots"""
    _events: List = field(default_factory=list, init=False, repr=False)
    
    def add_event(self, event) -> None:
        """Add a domain event"""
        self._events.append(event)
    
    @property
    def events(self) -> List:
        """Get all pending domain events"""
        return self._events.copy()
    
    def clear_events(self) -> None:
        """Clear all pending domain events"""
        self._events.clear()

@dataclass
class Order(AggregateRoot):
    """Order aggregate root"""
    id: UUID = field(default_factory=uuid4)
    customer_id: UUID
    items: List['OrderItem'] = field(default_factory=list)
    status: str = "new"
    
    def add_item(self, product_id: UUID, quantity: int, price: Money) -> None:
        """Add an item to the order"""
        # Business rule: Quantity must be positive
        if quantity <= 0:
            raise ValueError("Quantity must be positive")
        
        # Check if item already exists
        for item in self.items:
            if item.product_id == product_id:
                # Update quantity instead of adding new item
                item.quantity += quantity
                self.add_event(OrderItemQuantityChanged(order_id=self.id, 
                                                      product_id=product_id,
                                                      new_quantity=item.quantity))
                return
        
        # Add new item
        item = OrderItem(
            id=uuid4(),
            order_id=self.id,
            product_id=product_id,
            quantity=quantity,
            price=price
        )
        self.items.append(item)
        self.add_event(OrderItemAdded(order_id=self.id, item=item))
    
    def remove_item(self, product_id: UUID) -> None:
        """Remove an item from the order"""
        for i, item in enumerate(self.items):
            if item.product_id == product_id:
                removed_item = self.items.pop(i)
                self.add_event(OrderItemRemoved(order_id=self.id, item=removed_item))
                return
        
        raise ValueError(f"Product {product_id} not in order")
    
    def place(self) -> None:
        """Place the order"""
        # Business rule: Can't place an empty order
        if not self.items:
            raise ValueError("Cannot place an empty order")
        
        # Business rule: Can only place orders in 'new' status
        if self.status != "new":
            raise ValueError(f"Cannot place order with status '{self.status}'")
        
        self.status = "placed"
        self.add_event(OrderPlaced(order_id=self.id))
    
    def cancel(self) -> None:
        """Cancel the order"""
        # Business rule: Can't cancel shipped orders
        if self.status == "shipped":
            raise ValueError("Cannot cancel shipped order")
        
        self.status = "cancelled"
        self.add_event(OrderCancelled(order_id=self.id))

@dataclass(eq=False)
class OrderItem(Entity):
    """Order item entity"""
    id: UUID = field(default_factory=uuid4)
    order_id: UUID
    product_id: UUID
    quantity: int
    price: Money
    
    @property
    def total_price(self) -> Money:
        """Calculate the total price for this item"""
        return self.price * self.quantity
```

### Domain events template

```python
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

@dataclass(frozen=True)
class DomainEvent:
    """Base class for all domain events"""
    event_id: UUID = field(default_factory=uuid4)
    occurred_on: datetime = field(default_factory=datetime.now)

@dataclass(frozen=True)
class OrderPlaced(DomainEvent):
    """Event raised when an order is placed"""
    order_id: UUID

@dataclass(frozen=True)
class OrderCancelled(DomainEvent):
    """Event raised when an order is cancelled"""
    order_id: UUID

@dataclass(frozen=True)
class OrderItemAdded(DomainEvent):
    """Event raised when an item is added to an order"""
    order_id: UUID
    item: Any

@dataclass(frozen=True)
class OrderItemRemoved(DomainEvent):
    """Event raised when an item is removed from an order"""
    order_id: UUID
    item: Any

@dataclass(frozen=True)
class OrderItemQuantityChanged(DomainEvent):
    """Event raised when an item quantity is changed"""
    order_id: UUID
    product_id: UUID
    new_quantity: int
```

### Repository template

```python
from abc import ABC, abstractmethod
from typing import List, Optional, Protocol
from uuid import UUID

# Domain layer - Repository interface using Protocol (Python 3.8+)
class OrderRepository(Protocol):
    """Repository interface for Order aggregates"""
    def save(self, order: Order) -> None:
        """Save an order"""
        ...
    
    def find_by_id(self, order_id: UUID) -> Optional[Order]:
        """Find an order by ID"""
        ...
    
    def find_by_customer_id(self, customer_id: UUID) -> List[Order]:
        """Find all orders for a customer"""
        ...

# Infrastructure layer - Concrete implementation
class SQLAlchemyOrderRepository:
    """SQLAlchemy implementation of OrderRepository"""
    
    def __init__(self, session):
        self.session = session
        self.event_publisher = EventPublisher()
    
    def save(self, order: Order) -> None:
        """Save an order and publish its events"""
        # Convert domain objects to ORM models
        order_model = self._to_model(order)
        
        # Save to database
        self.session.add(order_model)
        
        # Publish domain events
        for event in order.events:
            self.event_publisher.publish(event)
        
        # Clear events after publishing
        order.clear_events()
        
        self.session.commit()
    
    def find_by_id(self, order_id: UUID) -> Optional[Order]:
        """Find an order by ID"""
        order_model = self.session.query(OrderModel).filter_by(id=str(order_id)).first()
        
        if not order_model:
            return None
            
        return self._to_entity(order_model)
    
    def find_by_customer_id(self, customer_id: UUID) -> List[Order]:
        """Find all orders for a customer"""
        order_models = self.session.query(OrderModel).filter_by(customer_id=str(customer_id)).all()
        return [self._to_entity(model) for model in order_models]
    
    def _to_model(self, order: Order) -> OrderModel:
        """Convert domain entity to ORM model"""
        # Implementation details
        pass
    
    def _to_entity(self, model: OrderModel) -> Order:
        """Convert ORM model to domain entity"""
        # Implementation details
        pass
```

### Message bus template

```python
from typing import Any, Callable, Dict, List, Type

class MessageBus:
    """Simple implementation of a message bus"""
    
    def __init__(self):
        self.handlers: Dict[Type, List[Callable]] = {}
    
    def register(self, event_type: Type, handler: Callable[[Any], None]) -> None:
        """Register a handler for an event type"""
        if event_type not in self.handlers:
            self.handlers[event_type] = []
        self.handlers[event_type].append(handler)
    
    def publish(self, event: Any) -> None:
        """Publish an event to all registered handlers"""
        event_type = type(event)
        if event_type in self.handlers:
            for handler in self.handlers[event_type]:
                handler(event)
```

### Sample domain service

```python
class DiscountService:
    """Domain service for applying discounts to orders"""
    
    def apply_discount(self, order: Order, discount_percentage: float) -> Order:
        """Apply a percentage discount to an order"""
        if discount_percentage < 0 or discount_percentage > 100:
            raise ValueError("Discount percentage must be between 0 and 100")
        
        if order.status != "new":
            raise ValueError(f"Cannot apply discount to order with status '{order.status}'")
        
        for item in order.items:
            discount_multiplier = 1 - (discount_percentage / 100)
            discounted_amount = item.price.amount * Decimal(str(discount_multiplier))
            
            # Create a new Money object with the discounted amount
            discounted_price = Money(discounted_amount, item.price.currency)
            
            # Update the item price
            object.__setattr__(item, "price", discounted_price)
        
        # Add a domain event
        order.add_event(DiscountApplied(
            order_id=order.id,
            discount_percentage=discount_percentage
        ))
        
        return order
```

### Anti-corruption layer example

```python
class LegacyOrderAdapter:
    """Anti-corruption layer for legacy order system"""
    
    def __init__(self, legacy_api_client):
        self.legacy_client = legacy_api_client
    
    def get_order(self, legacy_order_number: str) -> Order:
        """Retrieve order from legacy system and convert to domain model"""
        # Get data from legacy system
        legacy_data = self.legacy_client.get_order(legacy_order_number)
        
        # Map legacy status codes to domain status
        status_map = {
            "N": "new",
            "P": "processing",
            "S": "shipped",
            "C": "cancelled",
            "D": "delivered"
        }
        
        # Create domain order
        order = Order(
            customer_id=self._map_customer_id(legacy_data["customer_code"]),
            status=status_map.get(legacy_data["status_code"], "unknown")
        )
        
        # Add items from legacy data
        for item_data in legacy_data["line_items"]:
            order.add_item(
                product_id=self._map_product_id(item_data["product_code"]),
                quantity=int(item_data["qty"]),
                price=Money(
                    amount=Decimal(str(item_data["unit_price"])),
                    currency="USD"  # Assuming legacy system uses USD
                )
            )
        
        return order
    
    def _map_customer_id(self, customer_code: str) -> UUID:
        """Map legacy customer code to domain customer ID"""
        # This would typically involve a database lookup
        # Simplified example:
        customer_mapping = {
            "CUST001": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
            "CUST002": "6ec0bd7f-11c0-43da-975e-2a8ad9ebae0b"
        }
        return UUID(customer_mapping.get(customer_code, "00000000-0000-0000-0000-000000000000"))
    
    def _map_product_id(self, product_code: str) -> UUID:
        """Map legacy product code to domain product ID"""
        # This would typically involve a database lookup
        # Simplified example:
        product_mapping = {
            "PROD001": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
            "PROD002": "550e8400-e29b-41d4-a716-446655440000"
        }
        return UUID(product_mapping.get(product_code, "00000000-0000-0000-0000-000000000000"))
```

### Command Query Responsibility Segregation (CQRS) example

```python
from dataclasses import dataclass
from uuid import UUID
from typing import List, Optional

# Command (write model)
@dataclass
class CreateOrderCommand:
    customer_id: UUID
    items: List[dict]  # product_id, quantity, price details

# Command handler
class CreateOrderHandler:
    def __init__(self, order_repository: OrderRepository):
        self.order_repository = order_repository
    
    def handle(self, command: CreateOrderCommand) -> UUID:
        # Create order aggregate
        order = Order(customer_id=command.customer_id)
        
        # Add items
        for item in command.items:
            order.add_item(
                product_id=UUID(item["product_id"]),
                quantity=item["quantity"],
                price=Money(Decimal(str(item["price_amount"])), item["price_currency"])
            )
        
        # Apply business rules by calling domain method
        order.place()
        
        # Persist
        self.order_repository.save(order)
        
        return order.id

# Query (read model)
@dataclass
class OrderSummaryDTO:
    """Data Transfer Object for order summary"""
    id: UUID
    customer_id: UUID
    status: str
    item_count: int
    total_amount: str
    currency: str

# Query handler (reads from specialized read model)
class GetOrderSummaryHandler:
    def __init__(self, db_session):
        self.session = db_session
    
    def handle(self, order_id: UUID) -> Optional[OrderSummaryDTO]:
        # Direct optimized query to read database
        result = self.session.execute("""
            SELECT o.id, o.customer_id, o.status, 
                   COUNT(i.id) as item_count,
                   SUM(i.quantity * i.price_amount) as total_amount,
                   i.price_currency as currency
            FROM orders o
            JOIN order_items i ON o.id = i.order_id
            WHERE o.id = :order_id
            GROUP BY o.id, o.customer_id, o.status, i.price_currency
        """, {"order_id": str(order_id)}).fetchone()
        
        if not result:
            return None
        
        return OrderSummaryDTO(
            id=UUID(result.id),
            customer_id=UUID(result.customer_id),
            status=result.status,
            item_count=result.item_count,
            total_amount=str(result.total_amount),
            currency=result.currency
        )
```

### Unit of Work pattern for transactions

```python
from contextlib import contextmanager
from typing import Iterator, Optional

class UnitOfWork:
    """Abstract Unit of Work for managing transaction boundaries"""
    
    def __enter__(self):
        """Start a new transaction"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """End transaction (commit or rollback based on exception)"""
        if exc_type is not None:
            self.rollback()
        else:
            self.commit()
    
    def commit(self):
        """Commit the transaction"""
        pass
    
    def rollback(self):
        """Rollback the transaction"""
        pass

class SQLAlchemyUnitOfWork(UnitOfWork):
    """SQLAlchemy implementation of Unit of Work"""
    
    def __init__(self, session_factory):
        self.session_factory = session_factory
        self.session = None
    
    def __enter__(self):
        """Start a new database session"""
        self.session = self.session_factory()
        
        # Expose repositories
        self.orders = SQLAlchemyOrderRepository(self.session)
        self.customers = SQLAlchemyCustomerRepository(self.session)
        self.products = SQLAlchemyProductRepository(self.session)
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Close the session (and commit or rollback)"""
        try:
            super().__exit__(exc_type, exc_val, exc_tb)
        finally:
            self.session.close()
    
    def commit(self):
        """Commit the database transaction"""
        self.session.commit()
    
    def rollback(self):
        """Rollback the database transaction"""
        self.session.rollback()

# Usage example
@contextmanager
def get_unit_of_work() -> Iterator[UnitOfWork]:
    """Dependency provider for UnitOfWork"""
    uow = SQLAlchemyUnitOfWork(SessionFactory)
    try:
        yield uow
    finally:
        pass  # Session is closed in __exit__

# In application service
def create_order(customer_id: UUID, items: List[dict]) -> UUID:
    """Create a new order"""
    with get_unit_of_work() as uow:
        # Check customer exists
        customer = uow.customers.find_by_id(customer_id)
        if not customer:
            raise ValueError(f"Customer {customer_id} not found")
        
        # Create order
        order = Order(customer_id=customer_id)
        
        # Add items and verify product availability
        for item in items:
            product_id = UUID(item["product_id"])
            product = uow.products.find_by_id(product_id)
            
            if not product:
                raise ValueError(f"Product {product_id} not found")
            
            if not product.available:
                raise ValueError(f"Product {product.name} is not available")
            
            order.add_item(
                product_id=product_id,
                quantity=item["quantity"],
                price=product.price
            )
        
        # Place order
        order.place()
        
        # Save order and commit transaction
        uow.orders.save(order)
        
        return order.id
```

### Complete e-commerce example

Here's a more complete example showing a small e-commerce domain:

```python
# Value Objects
@dataclass(frozen=True, slots=True)
class Money:
    amount: Decimal
    currency: str
    
    def __post_init__(self):
        if isinstance(self.amount, (int, float)):
            object.__setattr__(self, "amount", Decimal(str(self.amount)))
        if self.amount < 0:
            raise ValueError("Amount cannot be negative")
        if len(self.currency) != 3:
            raise ValueError("Currency must be a 3-letter code")

# Entities and Aggregates
@dataclass
class Product(AggregateRoot):
    id: UUID = field(default_factory=uuid4)
    name: str
    description: str
    price: Money
    inventory_count: int = 0
    
    def update_inventory(self, count: int) -> None:
        if count < 0:
            raise ValueError("Inventory count cannot be negative")
        
        previous_count = self.inventory_count
        self.inventory_count = count
        
        self.add_event(ProductInventoryUpdated(
            product_id=self.id,
            previous_count=previous_count,
            new_count=count
        ))

@dataclass
class Order(AggregateRoot):
    id: UUID = field(default_factory=uuid4)
    customer_id: UUID
    shipping_address: Optional[str] = None
    status: str = "draft"
    items: List['OrderItem'] = field(default_factory=list)
    
    def add_item(self, product_id: UUID, product_name: str, price: Money, quantity: int) -> None:
        if quantity <= 0:
            raise ValueError("Quantity must be positive")
        
        # Check if product already in order
        for item in self.items:
            if item.product_id == product_id:
                item.quantity += quantity
                return
        
        # Add new item
        item = OrderItem(
            product_id=product_id,
            product_name=product_name,
            unit_price=price,
            quantity=quantity
        )
        self.items.append(item)
    
    def set_shipping_address(self, address: str) -> None:
        if not address:
            raise ValueError("Shipping address cannot be empty")
        self.shipping_address = address
    
    def calculate_total(self) -> Money:
        if not self.items:
            return Money(0, "USD")  # Default currency
        
        currency = self.items[0].unit_price.currency
        total = sum(item.unit_price.amount * item.quantity for item in self.items)
        
        return Money(total, currency)
    
    def place(self) -> None:
        if self.status != "draft":
            raise ValueError(f"Cannot place order with status '{self.status}'")
        
        if not self.items:
            raise ValueError("Cannot place an empty order")
        
        if not self.shipping_address:
            raise ValueError("Shipping address is required")
        
        self.status = "placed"
        self.add_event(OrderPlaced(order_id=self.id))
    
    def ship(self) -> None:
        if self.status != "placed":
            raise ValueError(f"Cannot ship order with status '{self.status}'")
        
        self.status = "shipped"
        self.add_event(OrderShipped(order_id=self.id))
    
    def complete(self) -> None:
        if self.status != "shipped":
            raise ValueError(f"Cannot complete order with status '{self.status}'")
        
        self.status = "completed"
        self.add_event(OrderCompleted(order_id=self.id))
    
    def cancel(self) -> None:
        if self.status in ["shipped", "completed"]:
            raise ValueError(f"Cannot cancel order with status '{self.status}'")
        
        self.status = "cancelled"
        self.add_event(OrderCancelled(order_id=self.id))

@dataclass
class OrderItem:
    product_id: UUID
    product_name: str
    unit_price: Money
    quantity: int
    
    @property
    def total_price(self) -> Money:
        return Money(self.unit_price.amount * self.quantity, self.unit_price.currency)

# Domain Service
class InventoryService:
    def __init__(self, product_repository):
        self.product_repository = product_repository
    
    def check_availability(self, order: Order) -> bool:
        """Check if all items in the order are available in sufficient quantity"""
        for item in order.items:
            product = self.product_repository.find_by_id(item.product_id)
            if not product or product.inventory_count < item.quantity:
                return False
        return True
    
    def reserve_inventory(self, order: Order) -> None:
        """Reserve inventory for all items in the order"""
        for item in order.items:
            product = self.product_repository.find_by_id(item.product_id)
            if not product:
                raise ValueError(f"Product {item.product_id} not found")
                
            if product.inventory_count < item.quantity:
                raise ValueError(f"Insufficient inventory for product {product.name}")
            
            # Update inventory
            product.update_inventory(product.inventory_count - item.quantity)
            self.product_repository.save(product)

# Application Service
class OrderService:
    def __init__(self, order_repository, product_repository, inventory_service):
        self.order_repository = order_repository
        self.product_repository = product_repository
        self.inventory_service = inventory_service
    
    def create_order(self, customer_id: UUID) -> UUID:
        """Create a new draft order"""
        order = Order(customer_id=customer_id)
        self.order_repository.save(order)
        return order.id
    
    def add_item_to_order(self, order_id: UUID, product_id: UUID, quantity: int) -> None:
        """Add an item to an order"""
        order = self.order_repository.find_by_id(order_id)
        if not order:
            raise ValueError(f"Order {order_id} not found")
        
        product = self.product_repository.find_by_id(product_id)
        if not product:
            raise ValueError(f"Product {product_id} not found")
        
        order.add_item(
            product_id=product.id,
            product_name=product.name,
            price=product.price,
            quantity=quantity
        )
        
        self.order_repository.save(order)
    
    def place_order(self, order_id: UUID, shipping_address: str) -> None:
        """Place an order"""
        order = self.order_repository.find_by_id(order_id)
        if not order:
            raise ValueError(f"Order {order_id} not found")
        
        # Set shipping address
        order.set_shipping_address(shipping_address)
        
        # Check inventory availability
        if not self.inventory_service.check_availability(order):
            raise ValueError("Some items in the order are not available in sufficient quantity")
        
        # Place the order
        order.place()
        
        # Reserve inventory
        self.inventory_service.reserve_inventory(order)
        
        # Save the order
        self.order_repository.save(order)
```

## Part D: Python libraries and frameworks for DDD

### Core DDD libraries

#### 1. Python Event Sourcing (pyeventsourcing/eventsourcing)

A comprehensive framework for implementing event sourcing, a cornerstone pattern for many DDD implementations.

**Key features:**
- Base classes for event-sourced aggregates and applications
- Flexible persistence of aggregate events
- Support for various databases
- Notifications and projections for CQRS
- Detailed documentation with type hints

**Pros:**
- Well-designed architecture with clear separation of concerns
- Full integration with Python type hints
- Extensive documentation and examples
- High test coverage
- Active development and maintenance

**Cons:**
- Learning curve for event sourcing concepts
- Requires understanding of DDD to use effectively

**Example:**
```python
from eventsourcing.domain import Aggregate, event
from eventsourcing.application import Application

class Product(Aggregate):
    @event('Created')
    def __init__(self, name, price):
        self.name = name
        self.price = price
        self.available = True
        
    @event('PriceChanged')
    def change_price(self, price):
        self.price = price
        
    @event('MarkedUnavailable')
    def mark_unavailable(self):
        self.available = False

class ProductCatalog(Application):
    def create_product(self, name, price):
        product = Product(name, price)
        self.save(product)
        return product.id
        
    def change_price(self, product_id, price):
        product = self.repository.get(product_id)
        product.change_price(price)
        self.save(product)
```

#### 2. dddpy

A template and toolkit for implementing DDD in Python applications, particularly focused on integrating with web frameworks like FastAPI.

**Key features:**
- Clear separation of domain, application, and infrastructure layers
- Repository pattern implementation
- Support for command and query segregation
- Value objects and entities

**Pros:**
- Well-structured example of a layered architecture
- Good integration with FastAPI
- Docker-based development environment

**Cons:**
- More of a template than a framework
- Limited documentation

**Example:**
```python
# Domain entity
class Todo:
    def __init__(self, id: TodoId, title: str, description: str = None):
        self.id = id
        self.title = title
        self.description = description
        self.status = "not_started"

# Repository interface in domain layer
class TodoRepository(ABC):
    @abstractmethod
    def find_by_id(self, todo_id: TodoId) -> Optional[Todo]:
        pass
        
    @abstractmethod
    def save(self, todo: Todo) -> None:
        pass
```

### ORM libraries with DDD support

#### 1. SQLAlchemy

The most popular ORM for Python, providing excellent support for implementing DDD patterns.

**Key features:**
- Powerful ORM with a clean domain model approach
- Integration with Python's type annotations
- Support for declarative models that map to domain entities
- Support for Python dataclasses in mapped classes
- Transaction management for aggregate consistency

**Pros:**
- Mature, stable, and actively maintained
- Excellent documentation and large community
- Support for virtually all relational databases
- Allows separation of domain model and persistence

**Cons:**
- Requires careful design to maintain true DDD separation
- Can be complex for beginners

**Example:**
```python
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase):
    pass

class OrderModel(Base):
    __tablename__ = "orders"
    
    id: Mapped[str] = mapped_column(primary_key=True)
    customer_id: Mapped[str]
    status: Mapped[str]

# Domain Repository using SQLAlchemy
class SQLAlchemyOrderRepository(OrderRepository):
    def __init__(self, session):
        self.session = session
        
    def find_by_id(self, order_id: UUID) -> Optional[Order]:
        order_model = self.session.query(OrderModel).filter_by(
            id=str(order_id)
        ).first()
        
        if not order_model:
            return None
            
        return self._to_entity(order_model)
```

#### 2. Django ORM

While Django's ORM follows more of an Active Record pattern, it can be adapted for DDD with proper abstractions.

**Pros:**
- Simple to use and well-documented
- Integrated with Django's ecosystem
- Good for rapid development

**Cons:**
- Tightly coupled with Django framework
- More Active Record than Domain Model pattern
- Requires additional abstraction layers for clean DDD

### Event sourcing and CQRS libraries

#### 1. Diator

A Python library designed for implementing the CQRS pattern, providing clean separation between read and write operations.

**Key features:**
- Command/Query separation
- Support for domain events, notification events
- Integration with message brokers
- Dependency injection support

**Pros:**
- Focused specifically on CQRS implementation
- Clean API design
- Supports asynchronous operations

**Cons:**
- Limited documentation
- Lower community adoption

**Example:**
```python
from diator.requests import Request, RequestHandler

@dataclass(frozen=True)
class CreateOrderCommand(Request):
    customer_id: UUID
    items: List[dict]

class CreateOrderCommandHandler(RequestHandler[CreateOrderCommand, UUID]):
    def __init__(self, order_repository) -> None:
        self.order_repository = order_repository
        self._events = []
        
    async def handle(self, request: CreateOrderCommand) -> UUID:
        order = Order(customer_id=request.customer_id)
        
        for item in request.items:
            order.add_item(
                product_id=item["product_id"],
                quantity=item["quantity"],
                price=Money(item["price_amount"], item["price_currency"])
            )
        
        order.place()
        self.order_repository.save(order)
        self._events.append(OrderCreatedEvent(order_id=order.id))
        
        return order.id
```

### Support libraries

#### 1. Pydantic

While not specifically a DDD library, Pydantic's data validation capabilities make it excellent for implementing value objects and entities in DDD.

**Key features:**
- Runtime data validation and parsing
- Type annotations support
- JSON Schema generation
- Settings management

**Pros:**
- Perfect for implementing value objects with validation
- Excellent performance
- Modern Python type annotations support

**Cons:**
- Not specifically designed for DDD
- Requires additional patterns for full DDD implementation

**Example:**
```python
from pydantic import BaseModel, Field, validator
from uuid import UUID, uuid4

class Email(BaseModel):
    value: str
    
    @validator('value')
    def validate_email(cls, v):
        if '@' not in v:
            raise ValueError('Invalid email format')
        return v.lower()
        
class User(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    name: str
    email: Email
```

#### 2. dependency-injector

A dependency injection framework that helps implement the dependency injection principle, valuable for DDD implementations.

**Key features:**
- Factory, Singleton, Callable providers
- Provider overriding for testing
- Configuration from various sources
- Resource management

**Pros:**
- Explicit dependency management
- Improves testability of code
- Cleaner, more maintainable structure

**Cons:**
- Learning curve for dependency injection concepts
- Some reported compatibility issues with Python 3.12

**Example:**
```python
from dependency_injector import containers, providers

class Container(containers.DeclarativeContainer):
    config = providers.Configuration()
    
    order_repository = providers.Factory(
        SQLAlchemyOrderRepository,
        session_factory=config.db.session_factory,
    )
    
    order_service = providers.Factory(
        OrderService,
        order_repository=order_repository,
    )
```

### Choosing the right libraries

When implementing DDD in Python 3.12 on Linux, consider these factors:

1. **Project complexity**: For simple projects, a combination of SQLAlchemy and Pydantic may be sufficient. For complex event-driven systems, consider Python Event Sourcing.

2. **Team experience**: If your team is new to DDD, start with libraries with good documentation like SQLAlchemy and gradually introduce more specialized libraries.

3. **Performance requirements**: Python 3.12's performance improvements with dataclasses and pattern matching optimize DDD implementations, but for high-performance needs, consider event sourcing and CQRS patterns.

4. **Maintainability**: Choose actively maintained libraries with good community support and compatibility with Python 3.12.

5. **Integration needs**: If you're building a web application, consider libraries with good integration with web frameworks like FastAPI or Django.

## Conclusion

Domain-Driven Design provides a powerful approach to tackling complex domains in Python 3.12 applications. By focusing on the business domain rather than technical implementations, DDD promotes maintainable, adaptable software that accurately reflects business needs.

Python 3.12's enhanced features like improved type annotations, dataclass optimizations, and pattern matching make implementing DDD patterns more efficient and expressive than ever, while Linux provides a stable, high-performance environment for running DDD applications.

Whether you're starting a new project or refactoring an existing one, the concepts, patterns, and examples in this guide provide a comprehensive foundation for implementing Domain-Driven Design successfully in your Python projects.