# Domain-Driven Design Framework for Python Developers

## Introduction

This framework provides a comprehensive, actionable guide to implementing Domain-Driven Design (DDD) in Python 3.12 applications. It's designed for experienced developers who want to apply DDD principles to create maintainable software that accurately reflects business needs.

---

## 1. What is Domain-Driven Design? First Principles & Fundamentals

### 1.1 Core Philosophy

Domain-Driven Design, introduced by Eric Evans in 2003, is a software development approach that connects implementation to an evolving model of the core business concepts. DDD's fundamental premise is that to build excellent software for complex domains:

- The primary focus should be on the domain and domain logic (not technology)
- Complex domain designs should be based on a model
- Technical experts and domain experts must collaborate to iteratively refine the model

**Key insight**: The most significant complexity in software is understanding the business domain itself, not the technology. DDD provides tools and processes to manage this complexity.

### 1.2 The Three Pillars of DDD

1. **Ubiquitous Language**: A common, shared language used by all team members to connect domain experts with technical experts
2. **Strategic Design**: Dividing complex domains into distinct areas (bounded contexts) and defining their relationships
3. **Tactical Design**: Implementation patterns for expressing domain models in code

### 1.3 Ubiquitous Language: Building a Shared Understanding

The ubiquitous language is a shared vocabulary that both domain experts and developers use consistently in all communications, documentation, and code.

**Characteristics of effective ubiquitous language**:

- Explicitly defined terms with precise meanings
- Continuously refined through collaboration
- Captured in documentation and code
- Used in all verbal and written communication
- Reflects the mental model of domain experts

**Python implementation example**:

```python
# Bad: Technical jargon disconnected from business domain
class UserDataProcessor:
    def process_user_transactions(self, user_id, transaction_list):
        pass

# Good: Reflects ubiquitous language of the business domain
class Customer:
    def make_purchase(self, shopping_cart):
        pass
```

### 1.4 Strategic Design: Managing Complexity at Scale

Strategic design provides tools for dealing with large-scale systems by dividing them into manageable contexts and defining relationships between these contexts.

#### 1.4.1 Bounded Contexts

A bounded context is a boundary within which a particular domain model is defined and applicable.

**Key characteristics**:

- Contains its own ubiquitous language
- Has clear boundaries defining where terms have specific meanings
- Typically aligns with subdomains of the business
- May be implemented as separate applications, modules, or services

**Python implementation example**:

```python
# Organizing code by bounded contexts
/ecommerce_system
    /catalog                # Catalog bounded context
        /domain
            product.py
            category.py
        /application
            product_service.py
        /infrastructure
            product_repository.py
    
    /order_management       # Order Management bounded context
        /domain
            order.py
            order_line.py
        /application
            order_service.py
        /infrastructure
            order_repository.py
```

#### 1.4.2 Context Mapping

Context mapping defines the relationships between bounded contexts.

**Common relationship patterns**:

- **Partnership**: Two teams collaborate on the integration of their contexts
- **Shared Kernel**: Multiple contexts share a subset of the domain model
- **Customer-Supplier**: Upstream/downstream relationship with formal contracts
- **Conformist**: Downstream team conforms to upstream team's model
- **Anti-Corruption Layer**: Translator prevents system corruption when integrating with external/legacy systems
- **Open Host Service**: Defines protocol for integrating with a subsystem
- **Published Language**: Provides translation between contexts

**Anti-corruption layer example in Python**:

```python
class LegacySystemAdapter:
    """Anti-corruption layer between modern system and legacy system"""
    
    def __init__(self, legacy_client):
        self.legacy_client = legacy_client
        
    def get_customer(self, customer_id: str) -> Customer:
        # Fetch data from legacy system
        legacy_data = self.legacy_client.get_customer_data(customer_id)
        
        # Translate to our domain model (using our ubiquitous language)
        return Customer(
            id=customer_id,
            name=legacy_data["customer_name"],
            email=legacy_data["email_address"],
            status="active" if legacy_data["status_code"] == "A" else "inactive"
        )
```

#### 1.4.3 Core, Supporting, and Generic Subdomains

DDD encourages focusing investment in the most valuable domains:

- **Core Domain**: The primary differentiator for the business, deserving the most investment
- **Supporting Domains**: Necessary for the business to operate but not a differentiator
- **Generic Domains**: Common across businesses, often candidates for off-the-shelf solutions

### 1.5 Tactical Design: Building Blocks for Domain Modeling

Tactical design provides specific implementation patterns to express the domain model in code.

#### 1.5.1 Entities

Entities are objects defined by their identity, not their attributes. They have continuity throughout the system lifecycle.

**Key characteristics**:

- Unique identity that persists across state changes
- Mutable attributes
- Equality based on identity (not attributes)
- Often represent business concepts with lifecycles

**Python implementation**:

```python
from dataclasses import dataclass
from uuid import UUID, uuid4
from typing import List, Optional

@dataclass
class Order:
    """Order entity with identity and behaviors"""
    id: UUID
    customer_id: UUID
    items: List['OrderItem']
    status: str = "draft"
    
    @classmethod
    def create(cls, customer_id: UUID) -> 'Order':
        """Factory method to create a new order"""
        return cls(
            id=uuid4(),
            customer_id=customer_id,
            items=[]
        )
    
    def add_item(self, product_id: UUID, quantity: int, price: float) -> None:
        """Add item to order (domain logic)"""
        if quantity <= 0:
            raise ValueError("Quantity must be positive")
            
        self.items.append(OrderItem(
            product_id=product_id,
            quantity=quantity,
            price=price
        ))
    
    def place(self) -> None:
        """Place the order (state change with validation)"""
        if not self.items:
            raise ValueError("Cannot place an empty order")
            
        self.status = "placed"
    
    def __eq__(self, other):
        if not isinstance(other, Order):
            return False
        return self.id == other.id
    
    def __hash__(self):
        return hash(self.id)
```

#### 1.5.2 Value Objects

Value objects are immutable objects defined by their attributes, not their identity.

**Key characteristics**:

- No identity
- Immutable
- Equality based on attributes
- Often represent measurements, descriptions, or attributes

**Python implementation**:

```python
from dataclasses import dataclass

@dataclass(frozen=True)  # frozen=True makes the class immutable
class Money:
    """Money value object with built-in validations and behaviors"""
    amount: float
    currency: str
    
    def __post_init__(self):
        # Validation in constructor
        if self.amount < 0:
            raise ValueError("Amount cannot be negative")
        if len(self.currency) != 3:
            raise ValueError("Currency must be a 3-letter code")
    
    def __add__(self, other):
        """Addition operator for adding money values"""
        if not isinstance(other, Money):
            return NotImplemented
        if self.currency != other.currency:
            raise ValueError(f"Cannot add money with different currencies: {self.currency} and {other.currency}")
        return Money(self.amount + other.amount, self.currency)
    
    def __mul__(self, multiplier: float):
        """Multiplication operator for calculating percentages, etc."""
        if not isinstance(multiplier, (int, float)):
            return NotImplemented
        return Money(self.amount * multiplier, self.currency)
```

#### 1.5.3 Aggregates

Aggregates group related entities and value objects into a cohesive unit with a clearly defined boundary.

**Key characteristics**:

- Cluster of associated objects treated as a unit for data changes
- Has a root entity (aggregate root) that provides the only access point to members
- Ensures consistency of changes to the objects within the aggregate
- Referenced from outside only by its identity

**Python implementation**:

```python
from dataclasses import dataclass, field
from typing import List, Optional
from uuid import UUID, uuid4

@dataclass
class OrderItem:
    """Entity within the Order aggregate"""
    product_id: UUID
    quantity: int
    price: Money
    
    @property
    def total(self) -> Money:
        return self.price * self.quantity

@dataclass
class Order:
    """Aggregate root for Order aggregate"""
    id: UUID = field(default_factory=uuid4)
    customer_id: UUID = field()
    shipping_address: Optional['Address'] = None
    items: List[OrderItem] = field(default_factory=list)
    status: str = "draft"
    
    # Methods to enforce invariants and consistency rules
    def add_item(self, product_id: UUID, quantity: int, price: Money) -> None:
        """Add item to order (enforces invariants)"""
        if quantity <= 0:
            raise ValueError("Quantity must be positive")
            
        # Check for existing product in order
        for item in self.items:
            if item.product_id == product_id:
                # Update quantity instead of adding duplicate
                item.quantity += quantity
                return
                
        self.items.append(OrderItem(
            product_id=product_id,
            quantity=quantity,
            price=price
        ))
    
    def place(self) -> None:
        """Place the order (enforces business rules)"""
        if not self.items:
            raise ValueError("Cannot place an empty order")
            
        if not self.shipping_address:
            raise ValueError("Shipping address is required")
            
        self.status = "placed"
    
    def calculate_total(self) -> Money:
        """Calculate order total (internal logic)"""
        if not self.items:
            return Money(0, "USD")  # Default empty order
            
        # Get currency from first item (assuming all same currency)
        currency = self.items[0].price.currency
        total = sum(item.total.amount for item in self.items)
        
        return Money(total, currency)
```

#### 1.5.4 Domain Services

Domain services encapsulate domain logic that doesn't naturally fit within an entity or value object.

**Key characteristics**:

- Stateless operations
- Encapsulates domain logic involving multiple entities
- Named after activities rather than things
- Not responsible for persistence

**Python implementation**:

```python
class DiscountService:
    """Domain service for calculating order discounts"""
    
    def apply_discount(self, order: Order, discount_code: str) -> Money:
        """Apply a discount to an order based on business rules"""
        # Domain logic for discount calculation
        if discount_code == "WELCOME10":
            return order.calculate_total() * 0.1
        elif discount_code == "BULK25" and any(item.quantity > 10 for item in order.items):
            return order.calculate_total() * 0.25
        elif discount_code == "SEASONAL":
            # Complex seasonal logic
            current_month = datetime.now().month
            if 6 <= current_month <= 8:  # Summer sale
                return order.calculate_total() * 0.15
            elif current_month == 12:  # Winter holiday
                return order.calculate_total() * 0.2
            else:
                return order.calculate_total() * 0.05
                
        # No valid discount found
        return Money(0, order.calculate_total().currency)
```

#### 1.5.5 Repositories

Repositories provide a way to obtain references to domain objects, abstracting the underlying infrastructure.

**Key characteristics**:

- Collection-like interface for accessing domain objects
- Encapsulates querying and persistence logic
- Operates at the aggregate level
- Domain-oriented abstraction over data storage

**Python implementation**:

```python
from abc import ABC, abstractmethod
from typing import List, Optional
from uuid import UUID

class OrderRepository(ABC):
    """Repository interface for Order aggregate"""
    
    @abstractmethod
    def save(self, order: Order) -> None:
        """Save an order to the repository"""
        pass
    
    @abstractmethod
    def get_by_id(self, order_id: UUID) -> Optional[Order]:
        """Get an order by its ID"""
        pass
    
    @abstractmethod
    def get_by_customer(self, customer_id: UUID) -> List[Order]:
        """Get all orders for a customer"""
        pass

# Concrete implementation (infrastructure layer)
class SQLAlchemyOrderRepository(OrderRepository):
    """SQLAlchemy implementation of OrderRepository"""
    
    def __init__(self, session):
        self.session = session
    
    def save(self, order: Order) -> None:
        """Save order to database"""
        self.session.add(order)
        self.session.commit()
    
    def get_by_id(self, order_id: UUID) -> Optional[Order]:
        """Get order by ID from database"""
        return self.session.query(Order).filter(Order.id == order_id).first()
    
    def get_by_customer(self, customer_id: UUID) -> List[Order]:
        """Get orders by customer from database"""
        return self.session.query(Order).filter(
            Order.customer_id == customer_id
        ).all()
```

#### 1.5.6 Factories

Factories encapsulate the logic for creating complex domain objects or aggregates.

**Key characteristics**:

- Hide complex object creation logic
- Ensure objects are created in a valid state
- Enforce invariants during creation
- Can recreate objects from persistence

**Python implementation**:

```python
class OrderFactory:
    """Factory for creating Order aggregates"""
    
    @staticmethod
    def create_new_order(customer_id: UUID) -> Order:
        """Create a new empty order"""
        return Order(
            id=uuid4(),
            customer_id=customer_id,
            items=[]
        )
    
    @staticmethod
    def create_order_with_items(
        customer_id: UUID, 
        items: List[dict]
    ) -> Order:
        """Create a new order with items"""
        order = Order(
            id=uuid4(),
            customer_id=customer_id,
            items=[]
        )
        
        # Add items to order
        for item in items:
            order.add_item(
                product_id=UUID(item["product_id"]),
                quantity=item["quantity"],
                price=Money(item["price_amount"], item["price_currency"])
            )
            
        return order
    
    @classmethod
    def recreate_from_persistence(cls, data: dict) -> Order:
        """Recreate an order from persistence data"""
        order = Order(
            id=UUID(data["id"]),
            customer_id=UUID(data["customer_id"]),
            shipping_address=Address(**data["shipping_address"]) if data.get("shipping_address") else None,
            status=data["status"],
            items=[]
        )
        
        # Recreate order items
        for item_data in data["items"]:
            order.items.append(OrderItem(
                product_id=UUID(item_data["product_id"]),
                quantity=item_data["quantity"],
                price=Money(item_data["price_amount"], item_data["price_currency"])
            ))
            
        return order
```

#### 1.5.7 Domain Events

Domain events represent something significant that happened in the domain.

**Key characteristics**:

- Immutable record of something that happened
- Named with a past-tense verb
- Can trigger workflows across bounded contexts
- Enable event-driven architecture

**Python implementation**:

```python
from dataclasses import dataclass, field
from datetime import datetime
from typing import List
from uuid import UUID, uuid4

@dataclass(frozen=True)
class DomainEvent:
    """Base class for all domain events"""
    id: UUID = field(default_factory=uuid4)
    occurred_on: datetime = field(default_factory=datetime.now)

@dataclass(frozen=True)
class OrderPlaced(DomainEvent):
    """Event representing an order being placed"""
    order_id: UUID
    customer_id: UUID
    total_amount: float
    currency: str

@dataclass
class AggregateRoot:
    """Base class for aggregate roots that generate domain events"""
    _events: List[DomainEvent] = field(default_factory=list, init=False, repr=False)
    
    def add_event(self, event: DomainEvent) -> None:
        """Add a domain event to this aggregate"""
        self._events.append(event)
    
    def clear_events(self) -> List[DomainEvent]:
        """Clear and return all events from this aggregate"""
        events = list(self._events)
        self._events.clear()
        return events

@dataclass
class Order(AggregateRoot):
    """Order aggregate that generates domain events"""
    id: UUID = field(default_factory=uuid4)
    customer_id: UUID = field()
    items: List[OrderItem] = field(default_factory=list)
    status: str = "draft"
    
    def place(self) -> None:
        """Place the order and generate domain event"""
        if not self.items:
            raise ValueError("Cannot place an empty order")
            
        self.status = "placed"
        
        # Generate domain event
        total = self.calculate_total()
        self.add_event(OrderPlaced(
            order_id=self.id,
            customer_id=self.customer_id,
            total_amount=total.amount,
            currency=total.currency
        ))
```

### 1.6 Python Execution of DDD Concepts

Python offers unique advantages and challenges for implementing DDD:

#### 1.6.1 Advantages of Python for DDD

- **Expressiveness**: Python's readability helps create a clear correlation between code and the ubiquitous language
- **Duck typing**: Allows for more flexible interfaces and adapters
- **Dataclasses**: Simplify the creation of entities and value objects
- **Type annotations**: Provide optional static typing for more robust domain models
- **Rich ecosystem**: Libraries like Pydantic, attrs, and SQLAlchemy support DDD implementation

#### 1.6.2 Challenges of Python for DDD

- **Dynamic typing**: Can make domain invariants less explicit
- **Mutability by default**: Requires extra care for value object immutability
- **No interfaces**: Must use abstract base classes or protocols instead
- **Performance considerations**: Complex domain models may have overhead

---

## 2. How to Apply Domain-Driven Design

This section provides concrete guidance on applying DDD principles in practice.

### 2.1 The DDD Implementation Process

Implementing DDD involves a series of iterative steps:

1. **Explore the domain**: Collaborate with domain experts to understand the business
2. **Distill a model**: Extract core concepts and relationships
3. **Develop ubiquitous language**: Create a shared vocabulary and glossary
4. **Create bounded contexts**: Divide the domain into cohesive areas
5. **Define context relationships**: Map how bounded contexts interact
6. **Implement domain models**: Create entities, value objects, and aggregates
7. **Evolve the model**: Continuously refine based on new understanding

#### 2.1.1 Explore the Domain: Practical Techniques

**Event Storming**

A collaborative workshop technique for capturing domain events, commands, and aggregates.

Steps for Event Storming in Python projects:
1. Gather domain experts and developers in a room with a large wall space
2. Use sticky notes to represent domain events (orange), commands (blue), aggregates (yellow)
3. Arrange events chronologically and identify causality
4. Group related events into potential aggregates
5. Identify bounded contexts based on natural divisions
6. Translate the model directly into Python classes and modules

**Example translation from Event Storming to Python code:**

```python
# Events identified during Event Storming
@dataclass(frozen=True)
class OrderPlaced(DomainEvent):
    order_id: UUID
    customer_id: UUID
    
@dataclass(frozen=True)
class PaymentReceived(DomainEvent):
    order_id: UUID
    amount: Money
    
@dataclass(frozen=True)
class OrderShipped(DomainEvent):
    order_id: UUID
    tracking_number: str

# Commands identified during Event Storming
@dataclass(frozen=True)
class PlaceOrder:
    customer_id: UUID
    items: List[dict]
    
@dataclass(frozen=True)
class ProcessPayment:
    order_id: UUID
    payment_method: str
    amount: Money

# Aggregates identified during Event Storming
@dataclass
class Order(AggregateRoot):
    id: UUID
    customer_id: UUID
    items: List[OrderItem]
    status: str = "draft"
    
    def place(self) -> None:
        """Place order command handler"""
        if not self.items:
            raise ValueError("Cannot place empty order")
        self.status = "placed"
        self.add_event(OrderPlaced(self.id, self.customer_id))
```

**Domain Storytelling**

A visual approach to understanding the domain by telling stories about business processes.

Steps for Domain Storytelling in Python projects:
1. Ask domain experts to "tell a story" about a business process
2. Record the story using a set of simple pictograms (actors, work objects, activities)
3. Identify domain objects and their behaviors
4. Translate these directly into Python classes and methods

#### 2.1.2 Distill a Model: From Domain Exploration to Code

After exploring the domain, distill the findings into a coherent model:

1. Identify key domain objects from your exploration sessions
2. Determine which should be entities vs value objects
3. Group related entities into aggregates
4. Define service boundaries for operations spanning multiple aggregates
5. Capture domain invariants as validation logic

**Example of transforming findings into Python code:**

```python
# Entity identified during domain exploration
@dataclass
class Product:
    id: UUID = field(default_factory=uuid4)
    name: str
    description: str
    price: Money
    stock_quantity: int = 0
    
    def restock(self, quantity: int) -> None:
        if quantity <= 0:
            raise ValueError("Restock quantity must be positive")
        self.stock_quantity += quantity

# Value object identified during domain exploration  
@dataclass(frozen=True)
class ShippingInfo:
    address: Address
    carrier: str
    method: str
    
    @property
    def estimated_days(self) -> int:
        if self.method == "express":
            return 1
        elif self.method == "standard":
            return 3
        else:
            return 7

# Domain service for logic spanning multiple entities
class InventoryService:
    def __init__(self, product_repository: ProductRepository):
        self.product_repository = product_repository
    
    def check_availability(self, order: Order) -> bool:
        """Check if order can be fulfilled based on inventory"""
        for item in order.items:
            product = self.product_repository.get_by_id(item.product_id)
            if not product or product.stock_quantity < item.quantity:
                return False
        return True
```

### 2.2 Strategic Design Implementation

#### 2.2.1 Identifying and Defining Bounded Contexts

Guidelines for identifying bounded contexts in Python projects:

- Look for natural divisions in terminology
- Consider team structures and system boundaries
- Identify areas with different data consistency requirements
- Look for distinct user personas or workflows

**Example bounded context organization in Python:**

```
/ecommerce_system
    /catalog                  # Catalog bounded context 
        /domain
            product.py        # Product aggregate
            category.py       # Category entity
        /application
            product_service.py
        /infrastructure
            product_repository.py
    
    /order_processing         # Order Processing bounded context
        /domain
            order.py          # Order aggregate
            payment.py        # Payment entity
        /application
            order_service.py
        /infrastructure
            order_repository.py
            payment_gateway.py
            
    /shipping                 # Shipping bounded context
        /domain
            shipment.py       # Shipment aggregate
            carrier.py        # Carrier entity
        /application
            shipping_service.py
        /infrastructure
            shipment_repository.py
            carrier_api.py
```

#### 2.2.2 Implementing Context Maps

Implement interactions between bounded contexts using well-defined patterns:

**Partnership example:**

```python
# Shared APIs between two bounded contexts that evolve together
# Order Processing context
class OrderService:
    def __init__(self, shipping_service: ShippingService):
        self.shipping_service = shipping_service
    
    def ship_order(self, order_id: UUID) -> None:
        """Ship an order by collaborating with shipping context"""
        order = self.order_repository.get_by_id(order_id)
        
        # Partnership relationship - direct collaboration
        shipment = self.shipping_service.create_shipment(
            order_id=order.id,
            shipping_address=order.shipping_address,
            items=order.items
        )
        
        order.mark_as_shipped(shipment.tracking_number)
        self.order_repository.save(order)
```

**Conformist example:**

```python
# Order context conforming to Payment context's model
# Payment bounded context (upstream)
class PaymentService:
    def process_payment(self, payment_request: PaymentRequest) -> PaymentResult:
        # Process payment using gateway
        return PaymentResult(...)

# Order bounded context (downstream - conformist)
class OrderPaymentService:
    def __init__(self, payment_service: PaymentService):
        self.payment_service = payment_service
    
    def pay_for_order(self, order: Order, payment_method: str) -> bool:
        # Conform to the upstream model (PaymentRequest)
        payment_request = PaymentRequest(
            amount=order.calculate_total().amount,
            currency=order.calculate_total().currency,
            payment_method=payment_method,
            reference_id=str(order.id)
        )
        
        # Using the upstream service directly
        result = self.payment_service.process_payment(payment_request)
        
        if result.success:
            order.mark_as_paid()
            return True
        return False
```

**Anti-corruption layer example:**

```python
# Order context protecting itself from a legacy inventory system
# Anti-corruption layer
class LegacyInventoryAdapter:
    """Anti-corruption layer for legacy inventory system"""
    
    def __init__(self, legacy_client):
        self.legacy_client = legacy_client
    
    def check_product_availability(self, product_id: UUID, quantity: int) -> bool:
        """Check product availability using the legacy system"""
        # Convert our domain ID to legacy system format
        legacy_product_id = str(product_id).replace('-', '').upper()
        
        # Call legacy system
        try:
            legacy_result = self.legacy_client.check_stock(
                item_number=legacy_product_id,
                qty=quantity
            )
            
            # Translate legacy response
            if legacy_result["status"] == "OK" and legacy_result["available"] == "Y":
                return True
            return False
        except Exception as e:
            # Handle legacy system errors
            logger.error(f"Legacy inventory system error: {e}")
            return False
        
# Using the anti-corruption layer
class OrderService:
    def __init__(self, inventory_adapter: LegacyInventoryAdapter):
        self.inventory_adapter = inventory_adapter
    
    def place_order(self, order: Order) -> bool:
        """Try to place an order"""
        # Check if all products are available
        for item in order.items:
            if not self.inventory_adapter.check_product_availability(
                item.product_id, item.quantity
            ):
                return False
        
        # Place the order
        order.place()
        return True
```

### 2.3 Tactical Design Implementation

#### 2.3.1 Python-Specific Entity Implementation 

Entities in Python should have a clear identity and maintain that identity even when attributes change.

**Decision: When to use entities**
- Use entities when object identity matters across the system
- Use entities for objects that have a lifecycle (are created, may change state, and potentially are archived/deleted)
- Use entities when you need to track an object even as its attributes change

**Implementation approaches:**

```python
# 1. Using dataclasses (recommended for most cases)
from dataclasses import dataclass, field
from uuid import UUID, uuid4

@dataclass
class Customer:
    """Customer entity"""
    id: UUID = field(default_factory=uuid4)
    name: str
    email: str
    status: str = "active"
    
    def deactivate(self) -> None:
        """Change customer status - entity state changes but identity remains"""
        self.status = "inactive"
    
    def update_email(self, new_email: str) -> None:
        """Update email address"""
        self.email = new_email
    
    def __eq__(self, other):
        if not isinstance(other, Customer):
            return False
        return self.id == other.id
    
    def __hash__(self):
        return hash(self.id)

# 2. Using a base entity class (for consistent entity behavior)
class Entity:
    """Base class for all entities"""
    id: UUID
    
    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        return self.id == other.id
    
    def __hash__(self):
        return hash(self.id)

@dataclass
class Product(Entity):
    """Product entity inheriting base entity behavior"""
    id: UUID = field(default_factory=uuid4)
    name: str
    description: str
    price: float
    category_id: UUID
```

#### 2.3.2 Value Object Implementations

Value objects in Python should be immutable and equatable by their attributes.

**Decision: When to use value objects**
- Use value objects when you care about attributes, not identity
- Use value objects for descriptive elements of the domain
- Use value objects for measurements, calculations, and multi-attribute concepts

**Implementation approaches:**

```python
# 1. Using frozen dataclasses (recommended)
from dataclasses import dataclass
from typing import Optional

@dataclass(frozen=True)
class Address:
    """Address value object"""
    street: str
    city: str
    state: str
    postal_code: str
    country: str
    unit: Optional[str] = None
    
    @property
    def formatted(self) -> str:
        """Format address for display"""
        unit_part = f" Unit {self.unit}" if self.unit else ""
        return f"{self.street}{unit_part}\n{self.city}, {self.state} {self.postal_code}\n{self.country}"

# 2. Using Pydantic (for additional validation)
from pydantic import BaseModel, field_validator
from typing import Optional
from decimal import Decimal

class Money(BaseModel):
    """Money value object with validation"""
    amount: Decimal
    currency: str
    
    @field_validator('amount')
    @classmethod
    def amount_must_be_positive(cls, v):
        if v < 0:
            raise ValueError('Amount cannot be negative')
        return v
    
    @field_validator('currency')
    @classmethod
    def currency_must_be_valid(cls, v):
        valid_currencies = {'USD', 'EUR', 'GBP', 'JPY', 'CAD'}
        if v not in valid_currencies:
            raise ValueError(f'Currency must be one of: {valid_currencies}')
        return v
    
    def __add__(self, other):
        if not isinstance(other, Money) or self.currency != other.currency:
            raise ValueError(f"Cannot add {self.currency} to {other.currency}")
        return Money(amount=self.amount + other.amount, currency=self.currency)
    
    def __mul__(self, multiplier: float) -> 'Money':
        return Money(amount=self.amount * Decimal(str(multiplier)), currency=self.currency)
    
    class Config:
        frozen = True  # Make immutable
```

#### 2.3.3 Aggregate Implementation 

Aggregates in Python group entities and value objects into a cohesive unit with a clearly defined boundary.

**Decision: When to define aggregates**
- Use aggregates to group entities that should change together
- Define aggregates around transactions and invariants
- Create aggregates when you need to enforce consistency rules across multiple objects

**Implementation approaches:**

```python
# Using dataclasses with type hints
from dataclasses import dataclass, field
from typing import List, Optional
from uuid import UUID, uuid4

@dataclass
class Order:
    """Order aggregate root"""
    id: UUID = field(default_factory=uuid4)
    customer_id: UUID
    items: List['OrderItem'] = field(default_factory=list)
    shipping_address: Optional[Address] = None
    status: str = "draft"
    
    def add_item(self, product_id: UUID, product_name: str, price: Money, quantity: int) -> None:
        """Add an item to the order"""
        # Business rule: Quantity must be positive
        if quantity <= 0:
            raise ValueError("Quantity must be positive")
            
        # Check for existing product in order
        for item in self.items:
            if item.product_id == product_id:
                # Update quantity instead of adding duplicate
                item.quantity += quantity
                return
                
        # Add new item
        self.items.append(OrderItem(
            product_id=product_id,
            product_name=product_name,
            price=price,
            quantity=quantity
        ))
    
    def remove_item(self, product_id: UUID) -> None:
        """Remove an item from the order"""
        self.items = [item for item in self.items if item.product_id != product_id]
    
    def place(self) -> None:
        """Place the order"""
        # Business rule: Order must have items
        if not self.items:
            raise ValueError("Cannot place an empty order")
            
        # Business rule: Shipping address required
        if not self.shipping_address:
            raise ValueError("Shipping address is required")
            
        # Update status
        self.status = "placed"
    
    def calculate_total(self) -> Money:
        """Calculate order total"""
        if not self.items:
            return Money(Decimal('0'), 'USD')
            
        # Sum all line totals (assumes same currency)
        currency = self.items[0].price.currency
        total = sum(item.price.amount * item.quantity for item in self.items)
        
        return Money(total, currency)

@dataclass
class OrderItem:
    """Entity within Order aggregate"""
    product_id: UUID
    product_name: str
    price: Money
    quantity: int
    
    @property
    def total(self) -> Money:
        """Calculate line total"""
        return self.price * self.quantity
```

**Key design considerations for aggregates:**

1. **Keep aggregates small**: Include only entities and value objects that must change together
2. **Reference other aggregates by identity**: Use IDs, not direct object references
3. **One transaction per aggregate**: Each transaction should modify only one aggregate
4. **Use eventual consistency between aggregates**: Don't force immediate consistency across aggregate boundaries

#### 2.3.4 Repository Implementation

Repositories abstract data access and provide a collection-like interface for domain objects.

**Decision: When to create repositories**
- Create one repository per aggregate type
- Use repositories to abstract persistence details from the domain model
- Implement repositories when you need to retrieve or store domain objects

**Implementation approaches:**

```python
# 1. Abstract Repository with Protocol (Python 3.8+)
from typing import Protocol, List, Optional
from uuid import UUID

class OrderRepository(Protocol):
    """Repository interface for Order aggregate"""
    
    def save(self, order: Order) -> None:
        """Save an order to persistent storage"""
        ...
    
    def get_by_id(self, order_id: UUID) -> Optional[Order]:
        """Get an order by ID"""
        ...
    
    def get_by_customer(self, customer_id: UUID) -> List[Order]:
        """Get all orders for a customer"""
        ...

# 2. SQLAlchemy Implementation
from sqlalchemy.orm import Session

class SQLAlchemyOrderRepository:
    """SQLAlchemy implementation of OrderRepository"""
    
    def __init__(self, session: Session):
        self.session = session
    
    def save(self, order: Order) -> None:
        """Save order to database"""
        self.session.add(order)
        self.session.commit()
    
    def get_by_id(self, order_id: UUID) -> Optional[Order]:
        """Get order by ID from database"""
        return self.session.query(Order).filter(Order.id == order_id).first()
    
    def get_by_customer(self, customer_id: UUID) -> List[Order]:
        """Get orders by customer from database"""
        return self.session.query(Order).filter(
            Order.customer_id == customer_id
        ).all()

# 3. In-Memory Repository (for testing)
class InMemoryOrderRepository:
    """In-memory implementation of OrderRepository for testing"""
    
    def __init__(self):
        self.orders = {}  # Dictionary of orders by ID
    
    def save(self, order: Order) -> None:
        """Save order to in-memory dictionary"""
        self.orders[order.id] = order
    
    def get_by_id(self, order_id: UUID) -> Optional[Order]:
        """Get order by ID from in-memory dictionary"""
        return self.orders.get(order_id)
    
    def get_by_customer(self, customer_id: UUID) -> List[Order]:
        """Get orders by customer from in-memory dictionary"""
        return [order for order in self.orders.values() 
                if order.customer_id == customer_id]
```

#### 2.3.5 Domain Service Implementation

Domain services encapsulate domain logic that doesn't naturally fit within entities or value objects.

**Decision: When to create domain services**
- Create domain services for operations that involve multiple domain objects
- Use domain services for complex domain logic that doesn't belong to a single entity
- Implement domain services for stateless operations within a bounded context

**Implementation approaches:**

```python
# 1. Simple Domain Service
class InventoryService:
    """Domain service for inventory operations"""
    
    def __init__(self, product_repository):
        self.product_repository = product_repository
    
    def allocate_inventory(self, order: Order) -> bool:
        """Allocate inventory for an order"""
        for item in order.items:
            product = self.product_repository.get_by_id(item.product_id)
            
            if not product:
                return False
                
            if product.stock_quantity < item.quantity:
                return False
                
            # Reduce inventory
            product.stock_quantity -= item.quantity
            self.product_repository.save(product)
            
        return True

# 2. Domain Service with Domain Events
class PaymentService:
    """Domain service for payment processing"""
    
    def __init__(self, payment_gateway, order_repository, event_publisher):
        self.payment_gateway = payment_gateway
        self.order_repository = order_repository
        self.event_publisher = event_publisher
    
    def process_payment(self, order_id: UUID, payment_method: str) -> bool:
        """Process payment for an order"""
        order = self.order_repository.get_by_id(order_id)
        
        if not order:
            raise ValueError(f"Order {order_id} not found")
            
        if order.status != "placed":
            raise ValueError(f"Cannot process payment for order with status {order.status}")
            
        # Call payment gateway
        payment_result = self.payment_gateway.charge(
            amount=order.calculate_total().amount,
            currency=order.calculate_total().currency,
            payment_method=payment_method,
            description=f"Order {order.id}"
        )
        
        if payment_result.success:
            # Update order status
            order.status = "paid"
            self.order_repository.save(order)
            
            # Publish domain event
            self.event_publisher.publish(PaymentReceived(
                order_id=order.id,
                amount=order.calculate_total(),
                payment_method=payment_method
            ))
            
            return True
        
        return False
```

#### 2.3.6 Domain Events Implementation

Domain events represent significant occurrences in the domain that other parts of the application might be interested in.

**Decision: When to use domain events**
- Use domain events to decouple bounded contexts
- Create domain events for significant state changes
- Implement domain events when multiple components need to react to the same occurrence

**Implementation approaches:**

```python
# 1. Simple domain events with dataclasses
from dataclasses import dataclass, field
from datetime import datetime
from typing import List
from uuid import UUID, uuid4

@dataclass(frozen=True)
class DomainEvent:
    """Base class for all domain events"""
    id: UUID = field(default_factory=uuid4)
    occurred_on: datetime = field(default_factory=datetime.now)

@dataclass(frozen=True)
class OrderPlaced(DomainEvent):
    """Event indicating an order has been placed"""
    order_id: UUID
    customer_id: UUID
    total_amount: float
    currency: str

# 2. Event publishing with aggregates
@dataclass
class AggregateRoot:
    """Base class for aggregate roots that can emit domain events"""
    _events: List[DomainEvent] = field(default_factory=list, init=False, repr=False)
    
    def add_event(self, event: DomainEvent) -> None:
        """Add a domain event to this aggregate"""
        self._events.append(event)
    
    def clear_events(self) -> List[DomainEvent]:
        """Clear and return all events from this aggregate"""
        events = list(self._events)
        self._events.clear()
        return events

@dataclass
class Order(AggregateRoot):
    """Order aggregate root that generates domain events"""
    id: UUID = field(default_factory=uuid4)
    customer_id: UUID
    items: List[OrderItem] = field(default_factory=list)
    status: str = "draft"
    
    def place(self) -> None:
        """Place the order and generate domain event"""
        if not self.items:
            raise ValueError("Cannot place an empty order")
            
        self.status = "placed"
        
        # Generate domain event
        total = self.calculate_total()
        self.add_event(OrderPlaced(
            order_id=self.id,
            customer_id=self.customer_id,
            total_amount=total.amount,
            currency=total.currency
        ))

# 3. Event handling
class EventPublisher:
    """Simple event publisher"""
    
    def __init__(self):
        self.handlers = {}  # Dict of event types to list of handlers
    
    def register(self, event_type, handler):
        """Register a handler for an event type"""
        if event_type not in self.handlers:
            self.handlers[event_type] = []
        self.handlers[event_type].append(handler)
    
    def publish(self, event: DomainEvent):
        """Publish an event to all registered handlers"""
        event_type = type(event)
        if event_type in self.handlers:
            for handler in self.handlers[event_type]:
                handler(event)

# Implementing event handlers
def order_placed_email_handler(event: OrderPlaced):
    """Send an email when an order is placed"""
    print(f"Sending email to customer {event.customer_id} for order {event.order_id}")
    # Email sending logic here

def order_placed_inventory_handler(event: OrderPlaced):
    """Allocate inventory when an order is placed"""
    print(f"Allocating inventory for order {event.order_id}")
    # Inventory allocation logic here

# Registering handlers
publisher = EventPublisher()
publisher.register(OrderPlaced, order_placed_email_handler)
publisher.register(OrderPlaced, order_placed_inventory_handler)
```

### 2.4 Additional Patterns and Extensions

#### 2.4.1 Command Query Responsibility Segregation (CQRS)

CQRS separates read and write operations to enable optimization of each side.

**Decision: When to use CQRS**
- Use CQRS when read and write requirements differ significantly
- Implement CQRS when you need different data models for reading vs. writing
- Consider CQRS when your system has a high read-to-write ratio

**Implementation approaches:**

```python
# Command side (writes)
from dataclasses import dataclass
from typing import List
from uuid import UUID

@dataclass(frozen=True)
class CreateOrderCommand:
    """Command to create a new order"""
    customer_id: UUID
    product_ids: List[UUID]
    quantities: List[int]

class OrderCommandHandler:
    """Handler for order-related commands"""
    
    def __init__(self, order_repository, product_repository):
        self.order_repository = order_repository
        self.product_repository = product_repository
    
    def handle_create_order(self, command: CreateOrderCommand) -> UUID:
        """Handle the CreateOrderCommand"""
        # Create order aggregate
        order = Order(customer_id=command.customer_id)
        
        # Add items to order
        for i, product_id in enumerate(command.product_ids):
            product = self.product_repository.get_by_id(product_id)
            if not product:
                raise ValueError(f"Product {product_id} not found")
                
            order.add_item(
                product_id=product.id,
                product_name=product.name,
                price=product.price,
                quantity=command.quantities[i]
            )
        
        # Save order
        self.order_repository.save(order)
        return order.id

# Query side (reads)
from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime

@dataclass
class OrderSummaryDTO:
    """Data Transfer Object for order summary"""
    id: UUID
    customer_id: UUID
    order_date: datetime
    status: str
    total_amount: float
    total_items: int

class OrderQueryService:
    """Service for order-related queries"""
    
    def __init__(self, db_connection):
        self.db_connection = db_connection
    
    def get_order_summary(self, order_id: UUID) -> Optional[OrderSummaryDTO]:
        """Get order summary by ID"""
        # Direct query to read database (optimized for reading)
        query = """
            SELECT o.id, o.customer_id, o.created_at, o.status,
                   SUM(i.price * i.quantity) as total_amount,
                   SUM(i.quantity) as total_items
            FROM orders o
            JOIN order_items i ON o.id = i.order_id
            WHERE o.id = %s
            GROUP BY o.id, o.customer_id, o.created_at, o.status
        """
        
        with self.db_connection.cursor() as cursor:
            cursor.execute(query, (str(order_id),))
            row = cursor.fetchone()
            
            if not row:
                return None
                
            return OrderSummaryDTO(
                id=UUID(row[0]),
                customer_id=UUID(row[1]),
                order_date=row[2],
                status=row[3],
                total_amount=float(row[4]),
                total_items=int(row[5])
            )
    
    def get_customer_orders(self, customer_id: UUID) -> List[OrderSummaryDTO]:
        """Get all orders for a customer"""
        # Direct query to read database (optimized for reading)
        query = """
            SELECT o.id, o.customer_id, o.created_at, o.status,
                   SUM(i.price * i.quantity) as total_amount,
                   SUM(i.quantity) as total_items
            FROM orders o
            JOIN order_items i ON o.id = i.order_id
            WHERE o.customer_id = %s
            GROUP BY o.id, o.customer_id, o.created_at, o.status
            ORDER BY o.created_at DESC
        """
        
        with self.db_connection.cursor() as cursor:
            cursor.execute(query, (str(customer_id),))
            results = []
            
            for row in cursor.fetchall():
                results.append(OrderSummaryDTO(
                    id=UUID(row[0]),
                    customer_id=UUID(row[1]),
                    order_date=row[2],
                    status=row[3],
                    total_amount=float(row[4]),
                    total_items=int(row[5])
                ))
                
            return results
```

#### 2.4.2 Event Sourcing

Event sourcing persists the state of a business entity as a sequence of state-changing events.

**Decision: When to use Event Sourcing**
- Use event sourcing when you need a complete audit trail
- Implement event sourcing for systems where the event history is valuable
- Consider event sourcing when temporal queries are important

**Implementation approaches:**

```python
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any, Type, Optional
from uuid import UUID, uuid4

# 1. Define events
@dataclass(frozen=True)
class DomainEvent:
    """Base class for all domain events"""
    aggregate_id: UUID
    version: int
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass(frozen=True)
class OrderCreated(DomainEvent):
    """Event indicating an order was created"""
    customer_id: UUID

@dataclass(frozen=True)
class OrderItemAdded(DomainEvent):
    """Event indicating an item was added to an order"""
    product_id: UUID
    product_name: str
    quantity: int
    price: float
    currency: str

@dataclass(frozen=True)
class OrderPlaced(DomainEvent):
    """Event indicating an order was placed"""
    shipping_address: Dict[str, Any]

# 2. Define event-sourced aggregate
class EventSourcedAggregate:
    """Base class for event-sourced aggregates"""
    id: UUID
    version: int = 0
    
    def apply_event(self, event: DomainEvent) -> None:
        """Apply an event to this aggregate"""
        # Find and call the appropriate event handler
        method_name = f"apply_{event.__class__.__name__}"
        method = getattr(self, method_name)
        method(event)
        
        # Update version
        self.version += 1

class Order(EventSourcedAggregate):
    """Event-sourced Order aggregate"""
    
    def __init__(self, id: UUID = None):
        """Initialize a new order"""
        self.id = id or uuid4()
        self.version = 0
        self.customer_id = None
        self.items = []
        self.status = "draft"
        self.shipping_address = None
    
    def create(self, customer_id: UUID) -> OrderCreated:
        """Create a new order"""
        event = OrderCreated(
            aggregate_id=self.id,
            version=self.version + 1,
            customer_id=customer_id
        )
        self.apply_event(event)
        return event
    
    def add_item(self, product_id: UUID, product_name: str, 
                 quantity: int, price: float, currency: str) -> OrderItemAdded:
        """Add an item to the order"""
        if quantity <= 0:
            raise ValueError("Quantity must be positive")
        
        event = OrderItemAdded(
            aggregate_id=self.id,
            version=self.version + 1,
            product_id=product_id,
            product_name=product_name,
            quantity=quantity,
            price=price,
            currency=currency
        )
        self.apply_event(event)
        return event
    
    def place(self, shipping_address: Dict[str, Any]) -> OrderPlaced:
        """Place the order"""
        if not self.items:
            raise ValueError("Cannot place an empty order")
        
        if not shipping_address:
            raise ValueError("Shipping address is required")
        
        event = OrderPlaced(
            aggregate_id=self.id,
            version=self.version + 1,
            shipping_address=shipping_address
        )
        self.apply_event(event)
        return event
    
    # Event handlers
    def apply_OrderCreated(self, event: OrderCreated) -> None:
        """Apply OrderCreated event"""
        self.customer_id = event.customer_id
    
    def apply_OrderItemAdded(self, event: OrderItemAdded) -> None:
        """Apply OrderItemAdded event"""
        self.items.append({
            'product_id': event.product_id,
            'product_name': event.product_name,
            'quantity': event.quantity,
            'price': event.price,
            'currency': event.currency
        })
    
    def apply_OrderPlaced(self, event: OrderPlaced) -> None:
        """Apply OrderPlaced event"""
        self.shipping_address = event.shipping_address
        self.status = "placed"

# 3. Repository for event-sourced aggregates
class EventStore:
    """Simple in-memory event store"""
    
    def __init__(self):
        self.events: Dict[UUID, List[DomainEvent]] = {}
    
    def save_events(self, aggregate_id: UUID, events: List[DomainEvent], 
                   expected_version: int) -> None:
        """Save events for an aggregate"""
        # Get existing events for this aggregate
        stored_events = self.events.get(aggregate_id, [])
        
        # Check version
        if stored_events and stored_events[-1].version != expected_version:
            raise ValueError(f"Concurrency conflict: expected version {expected_version}, but got {stored_events[-1].version}")
        
        # Store events
        if aggregate_id not in self.events:
            self.events[aggregate_id] = []
            
        self.events[aggregate_id].extend(events)
    
    def get_events(self, aggregate_id: UUID) -> List[DomainEvent]:
        """Get all events for an aggregate"""
        return self.events.get(aggregate_id, []).copy()

class OrderRepository:
    """Repository for event-sourced Order aggregates"""
    
    def __init__(self, event_store: EventStore):
        self.event_store = event_store
    
    def save(self, order: Order, new_events: List[DomainEvent]) -> None:
        """Save order by storing its new events"""
        if new_events:
            self.event_store.save_events(
                order.id,
                new_events,
                order.version - len(new_events)
            )
    
    def get_by_id(self, order_id: UUID) -> Optional[Order]:
        """Rebuild order from events"""
        events = self.event_store.get_events(order_id)
        
        if not events:
            return None
            
        # Create new order and apply all events
        order = Order(id=order_id)
        for event in events:
            order.apply_event(event)
            
        return order

# 4. Using the event-sourced aggregate
def create_order(repository: OrderRepository, customer_id: UUID) -> UUID:
    """Create a new order"""
    # Create order
    order = Order()
    events = [order.create(customer_id)]
    
    # Save events
    repository.save(order, events)
    
    return order.id

def add_item_to_order(repository: OrderRepository, order_id: UUID,
                     product_id: UUID, product_name: str,
                     quantity: int, price: float, currency: str) -> None:
    """Add an item to an order"""
    # Load order
    order = repository.get_by_id(order_id)
    if not order:
        raise ValueError(f"Order {order_id} not found")
    
    # Add item
    event = order.add_item(
        product_id=product_id,
        product_name=product_name,
        quantity=quantity,
        price=price,
        currency=currency
    )
    
    # Save event
    repository.save(order, [event])

def place_order(repository: OrderRepository, order_id: UUID,
               shipping_address: Dict[str, Any]) -> None:
    """Place an order"""
    # Load order
    order = repository.get_by_id(order_id)
    if not order:
        raise ValueError(f"Order {order_id} not found")
    
    # Place order
    event = order.place(shipping_address)
    
    # Save event
    repository.save(order, [event])
```

---

## 3. Pragmatic Development with DDD

This section focuses on practical aspects of implementing DDD, including common pitfalls, simplification strategies, and complementary patterns.

### 3.1 Common Pitfalls and How to Avoid Them

#### 3.1.1 Anemic Domain Model

**Pitfall**: Creating domain objects that are just data containers without behavior, keeping all logic in services.

**Example of anemic domain model:**

```python
# Anemic model - Just a data container
class Order:
    def __init__(self, id, customer_id, items=None, status="draft"):
        self.id = id
        self.customer_id = customer_id
        self.items = items or []
        self.status = status

# Service with all the business logic
class OrderService:
    def add_item(self, order, product_id, quantity, price):
        order.items.append({
            "product_id": product_id,
            "quantity": quantity,
            "price": price
        })
    
    def place_order(self, order):
        order.status = "placed"
    
    def calculate_total(self, order):
        return sum(item["price"] * item["quantity"] for item in order.items)
```

**How to avoid**: 
- Move behavior into domain objects
- Ensure business rules are enforced by the domain model itself
- Use encapsulation to protect invariants

**Improved approach:**

```python
class Order:
    def __init__(self, id, customer_id, items=None, status="draft"):
        self.id = id
        self.customer_id = customer_id
        self.items = items or []
        self.status = status
    
    def add_item(self, product_id, quantity, price):
        # Enforce business rules
        if quantity <= 0:
            raise ValueError("Quantity must be positive")
        
        self.items.append({
            "product_id": product_id,
            "quantity": quantity,
            "price": price
        })
    
    def place(self):
        # Enforce business rules
        if not self.items:
            raise ValueError("Cannot place an empty order")
        
        self.status = "placed"
    
    def calculate_total(self):
        return sum(item["price"] * item["quantity"] for item in self.items)
```

#### 3.1.2 Bloated Aggregates

**Pitfall**: Creating large aggregates that contain too many entities and value objects, leading to performance and concurrency issues.

**Example of bloated aggregate:**

```python
class Order:
    def __init__(self, id, customer, shipping_address, billing_address, payment_details, items=None):
        self.id = id
        self.customer = customer  # Entire Customer entity
        self.shipping_address = shipping_address
        self.billing_address = billing_address
        self.payment_details = payment_details
        self.items = items or []
        self.shipments = []  # List of Shipment entities
        self.invoices = []   # List of Invoice entities
```

**How to avoid**:
- Focus aggregates on consistency boundaries
- Reference other aggregates by ID, not by including the entire object
- Split large aggregates into smaller ones 
- Use eventual consistency between aggregates

**Improved approach:**

```python
class Order:
    def __init__(self, id, customer_id, shipping_address_id, billing_address_id, items=None):
        self.id = id
        self.customer_id = customer_id  # Just the ID, not the entire Customer
        self.shipping_address_id = shipping_address_id
        self.billing_address_id = billing_address_id
        self.items = items or []
        self.status = "draft"

# Separate aggregates for related concepts
class Payment:
    def __init__(self, id, order_id, amount, method, status="pending"):
        self.id = id
        self.order_id = order_id  # Reference to Order by ID
        self.amount = amount
        self.method = method
        self.status = status

class Shipment:
    def __init__(self, id, order_id, carrier, tracking_number, status="pending"):
        self.id = id
        self.order_id = order_id  # Reference to Order by ID
        self.carrier = carrier
        self.tracking_number = tracking_number
        self.status = status
```

#### 3.1.3 Misidentifying Aggregates

**Pitfall**: Incorrectly identifying aggregate boundaries, leading to consistency problems or performance issues.

**How to avoid**:
- Focus on business invariants to identify aggregates
- Consider what must be updated atomically
- Look for natural business transactions
- Use "Tell, Don't Ask" principle to enforce consistency

**Guidelines for identifying aggregates:**

1. Start with domain events and work backward
2. Consider which entities must always be consistent
3. Identify natural business transactions
4. Look for entities that are created and updated together
5. Evaluate performance and concurrency needs

**Example decision process:**

```
Question: Should Customer and Order be in the same aggregate?

Analysis:
- Does changing a customer require orders to change? No.
- Does placing an order require customer info to change? No.
- Can orders be processed if customer data is temporarily inconsistent? Yes.
- Is there a business invariant relating customers and orders? No.

Decision: Customer and Order should be separate aggregates, with Order referencing Customer by ID.
```

#### 3.1.4 Overengineering

**Pitfall**: Applying DDD patterns everywhere, even in simple parts of the application.

**How to avoid**:
- Apply DDD selectively to complex domains
- Use simpler patterns for CRUD-like functionality
- Consider the effort-to-value ratio for each pattern

**Decision matrix for when to apply DDD:**

| Domain Characteristic | Apply DDD? | Alternative Approach |
|-----------------------|------------|----------------------|
| Complex business rules | Yes | N/A |
| Simple CRUD operations | No | Basic service pattern or ORM |
| Evolving business processes | Yes | N/A |
| Stable, well-understood processes | Maybe | Use subset of DDD patterns |
| Team has domain experts available | Yes | N/A |
| Team lacks domain expertise | Limited | Start with bounded contexts and ubiquitous language |

### 3.2 Simplification Strategies

#### 3.2.1 Start with Core Domain Only

**Strategy**: Focus DDD efforts on the core domain first, using simpler patterns for supporting domains.

**Implementation:**

```python
# Core domain (Order Management) - Full DDD implementation
class Order(AggregateRoot):
    # Complex domain model with rich behavior
    # ...

# Supporting domain (User Management) - Simpler implementation
class User:
    def __init__(self, id, name, email):
        self.id = id
        self.name = name
        self.email = email

class UserRepository:
    def __init__(self, database):
        self.database = database
    
    def get_by_id(self, user_id):
        return self.database.query(User).filter_by(id=user_id).first()
    
    def save(self, user):
        self.database.add(user)
        self.database.commit()
```

#### 3.2.2 Use Transitional Architecture

**Strategy**: Implement DDD incrementally, gradually moving from a simpler architecture.

**Example migration stages:**

1. **Start with simple layered architecture**:
   ```
   /app
       /controllers
       /services
       /models
       /repositories
   ```

2. **Introduce bounded contexts**:
   ```
   /app
       /order_management
           /controllers
           /services
           /models
           /repositories
       /customer_management
           /controllers
           /services
           /models
           /repositories
   ```

3. **Evolve to DDD structure within core bounded contexts**:
   ```
   /app
       /order_management
           /domain
               /model
               /service
               /event
           /application
           /infrastructure
           /interfaces
       /customer_management
           /services  # Still using simpler architecture
           /models
           /repositories
   ```

#### 3.2.3 Use Lightweight Value Objects

**Strategy**: Simplify value objects by using less formal implementations while preserving immutability and validation.

**Example:**

```python
# Full DDD value object implementation
@dataclass(frozen=True)
class Money:
    amount: Decimal
    currency: str
    
    def __post_init__(self):
        if self.amount < 0:
            raise ValueError("Amount cannot be negative")
        
    def __add__(self, other):
        if not isinstance(other, Money) or self.currency != other.currency:
            raise ValueError("Cannot add different currencies")
        return Money(amount=self.amount + other.amount, currency=self.currency)
    
    def __mul__(self, multiplier):
        return Money(amount=self.amount * Decimal(str(multiplier)), currency=self.currency)

# Lightweight alternative
@dataclass(frozen=True)
class Money:
    amount: Decimal
    currency: str = "USD"
    
    def __post_init__(self):
        if self.amount < 0:
            raise ValueError("Amount cannot be negative")
```

#### 3.2.4 Use Application Services for Coordination

**Strategy**: Simplify domain model by moving orchestration logic to application services.

**Example:**

```python
# Application service coordinating multiple domain objects
class OrderProcessingService:
    def __init__(
        self,
        order_repository,
        payment_service,
        inventory_service,
        shipping_service,
        notification_service
    ):
        self.order_repository = order_repository
        self.payment_service = payment_service
        self.inventory_service = inventory_service
        self.shipping_service = shipping_service
        self.notification_service = notification_service
    
    def process_order(self, order_id: UUID) -> bool:
        """Process an order through all necessary steps"""
        # Load order
        order = self.order_repository.get_by_id(order_id)
        if not order or order.status != "placed":
            return False
        
        # Check inventory
        if not self.inventory_service.check_availability(order):
            order.mark_as_back_ordered()
            self.order_repository.save(order)
            self.notification_service.notify_customer_back_order(order)
            return False
        
        # Process payment
        payment_result = self.payment_service.charge_for_order(order)
        if not payment_result.success:
            order.mark_as_payment_failed()
            self.order_repository.save(order)
            self.notification_service.notify_customer_payment_failed(order)
            return False
        
        # Allocate inventory
        self.inventory_service.allocate_inventory(order)
        
        # Create shipment
        shipment = self.shipping_service.create_shipment(order)
        
        # Update order status
        order.mark_as_processing()
        self.order_repository.save(order)
        
        # Notify customer
        self.notification_service.notify_customer_order_processing(order, shipment)
        
        return True
```

### 3.3 Complementary Design Patterns

#### 3.3.1 Hexagonal Architecture (Ports and Adapters)

**Pattern**: Isolate the domain model from external concerns by defining ports (interfaces) and adapters (implementations).

**Benefits for DDD**:
- Protects domain model from infrastructure details
- Makes testing easier by allowing mock implementations
- Enables multiple user interfaces or persistence mechanisms

**Implementation example:**

```python
# Application core - domain model and ports
from abc import ABC, abstractmethod
from typing import List, Optional
from uuid import UUID

# Port (interface)
class OrderRepository(ABC):
    @abstractmethod
    def save(self, order: Order) -> None:
        pass
    
    @abstractmethod
    def get_by_id(self, order_id: UUID) -> Optional[Order]:
        pass

# Domain service that uses the port
class OrderService:
    def __init__(self, order_repository: OrderRepository):
        self.order_repository = order_repository
    
    def place_order(self, order: Order) -> None:
        # Domain logic
        order.place()
        self.order_repository.save(order)

# Adapter (implementation) - infrastructure layer
class SQLAlchemyOrderRepository(OrderRepository):
    def __init__(self, session):
        self.session = session
    
    def save(self, order: Order) -> None:
        self.session.add(order)
        self.session.commit()
    
    def get_by_id(self, order_id: UUID) -> Optional[Order]:
        return self.session.query(Order).filter_by(id=order_id).first()

# Another adapter for testing
class InMemoryOrderRepository(OrderRepository):
    def __init__(self):
        self.orders = {}
    
    def save(self, order: Order) -> None:
        self.orders[order.id] = order
    
    def get_by_id(self, order_id: UUID) -> Optional[Order]:
        return self.orders.get(order_id)
```

#### 3.3.2 Dependency Injection

**Pattern**: Provide dependencies to objects rather than having them create or find dependencies.

**Benefits for DDD**:
- Supports Hexagonal Architecture
- Makes testing easier
- Reduces coupling between components

**Implementation example with Python's dependency-injector:**

```python
from dependency_injector import containers, providers
from dependency_injector.wiring import inject, Provide

# Container setup
class Container(containers.DeclarativeContainer):
    config = providers.Configuration()
    
    # Database
    db_pool = providers.Singleton(
        create_db_pool,
        connection_string=config.db.connection_string
    )
    
    # Repositories
    order_repository = providers.Factory(
        SQLAlchemyOrderRepository,
        session_factory=db_pool.provided.session
    )
    
    # Domain services
    inventory_service = providers.Factory(
        InventoryService,
        product_repository=providers.Factory(
            SQLAlchemyProductRepository,
            session_factory=db_pool.provided.session
        )
    )
    
    # Application services
    order_service = providers.Factory(
        OrderService,
        order_repository=order_repository,
        inventory_service=inventory_service
    )

# Using dependencies in application
@inject
def place_order(
    order_data: dict,
    order_service: OrderService = Provide[Container.order_service]
):
    """API endpoint for placing an order"""
    # Create order from data
    order = Order(
        customer_id=UUID(order_data["customer_id"]),
        items=[
            OrderItem(
                product_id=UUID(item["product_id"]),
                quantity=item["quantity"],
                price=item["price"]
            ) for item in order_data["items"]
        ]
    )
    
    # Use injected service
    order_service.place_order(order)
    
    return {"order_id": str(order.id)}
```

#### 3.3.3 Unit of Work

**Pattern**: Maintain a list of objects affected by a business transaction and coordinate their persistence.

**Benefits for DDD**:
- Ensures aggregate consistency
- Simplifies transaction management
- Collects and handles domain events

**Implementation example:**

```python
from contextlib import contextmanager
from typing import Callable, Iterator

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

# Factory function for unit of work
@contextmanager
def get_unit_of_work() -> Iterator[UnitOfWork]:
    """Provide a Unit of Work"""
    uow = SQLAlchemyUnitOfWork(session_factory)
    try:
        yield uow
    finally:
        pass  # Session is closed in __exit__

# Using the Unit of Work pattern
def place_order(order_data: dict) -> UUID:
    """Place a new order"""
    with get_unit_of_work() as uow:
        # Create order
        order = Order(customer_id=UUID(order_data["customer_id"]))
        
        # Add items
        for item_data in order_data["items"]:
            product = uow.products.get_by_id(UUID(item_data["product_id"]))
            if not product:
                raise ValueError(f"Product {item_data['product_id']} not found")
                
            if product.stock_quantity < item_data["quantity"]:
                raise ValueError(f"Insufficient stock for product {product.name}")
                
            order.add_item(
                product_id=product.id,
                product_name=product.name,
                price=product.price,
                quantity=item_data["quantity"]
            )
        
        # Place order
        order.place()
        
        # Save order
        uow.orders.save(order)
        
        # Reduce inventory (part of the same transaction)
        for item in order.items:
            product = uow.products.get_by_id(item.product_id)
            product.stock_quantity -= item.quantity
            uow.products.save(product)
        
        # Transaction is committed at the end of the context
        
        return order.id
```

#### 3.3.4 Specification Pattern

**Pattern**: Create composable business rules that can be chained and combined.

**Benefits for DDD**:
- Encapsulates complex business rules
- Makes validation logic reusable
- Improves readability of domain logic

**Implementation example:**

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime, timedelta

# Base specification
class Specification(ABC):
    @abstractmethod
    def is_satisfied_by(self, candidate) -> bool:
        pass
    
    def and_(self, other: 'Specification') -> 'AndSpecification':
        return AndSpecification(self, other)
    
    def or_(self, other: 'Specification') -> 'OrSpecification':
        return OrSpecification(self, other)
    
    def not_(self) -> 'NotSpecification':
        return NotSpecification(self)

# Composite specifications
class AndSpecification(Specification):
    def __init__(self, left: Specification, right: Specification):
        self.left = left
        self.right = right
    
    def is_satisfied_by(self, candidate) -> bool:
        return self.left.is_satisfied_by(candidate) and self.right.is_satisfied_by(candidate)

class OrSpecification(Specification):
    def __init__(self, left: Specification, right: Specification):
        self.left = left
        self.right = right
    
    def is_satisfied_by(self, candidate) -> bool:
        return self.left.is_satisfied_by(candidate) or self.right.is_satisfied_by(candidate)

class NotSpecification(Specification):
    def __init__(self, wrapped: Specification):
        self.wrapped = wrapped
    
    def is_satisfied_by(self, candidate) -> bool:
        return not self.wrapped.is_satisfied_by(candidate)

# Domain-specific specifications
class ProductInStockSpecification(Specification):
    def is_satisfied_by(self, product) -> bool:
        return product.stock_quantity > 0

class PremiumCustomerSpecification(Specification):
    def is_satisfied_by(self, customer) -> bool:
        return customer.is_premium

class OrderValueOverSpecification(Specification):
    def __init__(self, minimum_value: float):
        self.minimum_value = minimum_value
    
    def is_satisfied_by(self, order) -> bool:
        return order.calculate_total().amount > self.minimum_value

# Using specifications
def apply_discount(order: Order, customer: Customer) -> bool:
    """Apply a discount based on specifications"""
    # Create specification for discount eligibility
    eligible_spec = (
        PremiumCustomerSpecification()
        .or_(OrderValueOverSpecification(1000))
    )
    
    # Check if customer/order meets the specification
    if eligible_spec.is_satisfied_by(customer):
        # Apply a 10% discount
        for item in order.items:
            item.price = item.price * 0.9
        return True
    
    return False
```

---

## 4. Bootstrapping DDD Projects

This section provides practical tools for quickly starting a DDD project.

### 4.1 Project Layouts

#### 4.1.1 Standard DDD Project Structure for Python

```
/project_name
    /src
        /domain                  # Domain layer
            /__init__.py
            /model               # Domain model
                /__init__.py
                /entities.py     # Entity definitions
                /value_objects.py # Value object definitions
                /aggregates.py   # Aggregate definitions
                /events.py       # Domain events
            /services            # Domain services
                /__init__.py
                /order_service.py
                /inventory_service.py
            /repositories        # Repository interfaces
                /__init__.py
                /order_repository.py
                /product_repository.py
            
        /application            # Application layer
            /__init__.py
            /services           # Application services
                /__init__.py
                /order_app_service.py
            /dtos               # Data Transfer Objects
                /__init__.py
                /order_dto.py
            /events             # Application events
                /__init__.py
                /order_events.py
            
        /infrastructure         # Infrastructure layer
            /__init__.py
            /repositories       # Repository implementations
                /__init__.py
                /sqlalchemy_repositories.py
            /persistence        # Database configuration
                /__init__.py
                /orm.py         # ORM configuration
                /models.py      # Database models
            /messaging          # Messaging infrastructure
                /__init__.py
                /rabbitmq.py
            
        /interfaces             # User interface layer
            /__init__.py
            /api                # API interfaces
                /__init__.py
                /rest           # REST API
                    /__init__.py
                    /order_controller.py
                /graphql        # GraphQL API
                    /__init__.py
                    /schema.py
            /cli                # Command line interface
                /__init__.py
                /commands.py
    
    /tests                      # Tests
        /unit                   # Unit tests
            /domain             # Domain tests
                /model          # Model tests
                    /test_entities.py
                    /test_aggregates.py
        /integration            # Integration tests
        /acceptance             # Acceptance tests
    
    /config                     # Configuration
        /__init__.py
        /settings.py
    
    /scripts                    # Scripts
        /migrations             # Database migrations
    
    setup.py                    # Package setup
    README.md                   # Project documentation
```

#### 4.1.2 Simplified Structure for Smaller Projects

```
/project_name
    /src
        /domain                  # Domain layer
            /__init__.py
            /model.py            # Domain model (entities, aggregates, value objects)
            /services.py         # Domain services
            /repositories.py     # Repository interfaces
        
        /application             # Application layer
            /__init__.py
            /services.py         # Application services
        
        /infrastructure          # Infrastructure layer
            /__init__.py
            /repositories.py     # Repository implementations
            /database.py         # Database configuration
        
        /interfaces              # User interface layer
            /__init__.py
            /api.py              # API endpoints
    
    /tests                       # Tests
        /test_domain.py          # Domain tests
        /test_application.py     # Application tests
    
    config.py                    # Configuration
    main.py                      # Application entry point
    README.md                    # Project documentation
```

#### 4.1.3 Microservices-Oriented Structure

```
/project_name
    /services
        /order_service
            /src
                /domain          # Domain layer
                    /__init__.py
                    /model.py    # Domain model
                    /services.py # Domain services
                
                /application     # Application layer
                    /__init__.py
                    /services.py # Application services
                
                /infrastructure  # Infrastructure layer
                    /__init__.py
                    /repositories.py
                    /database.py
                
                /api             # API layer
                    /__init__.py
                    /routes.py   # API routes
            
            /tests              # Tests for this service
            
            config.py           # Service configuration
            main.py             # Service entry point
        
        /inventory_service
            # Similar structure
        
        /customer_service
            # Similar structure
    
    /shared                     # Shared code
        /domain                 # Shared domain models
        /infrastructure         # Shared infrastructure
    
    docker-compose.yml          # Service orchestration
    README.md                   # Project documentation
```

### 4.2 Design Patterns and Templates

#### 4.2.1 Value Object Template

```python
from dataclasses import dataclass
from typing import Optional

@dataclass(frozen=True)  # frozen=True makes it immutable
class Address:
    """Address value object"""
    street: str
    city: str
    state: str
    postal_code: str
    country: str
    unit: Optional[str] = None
    
    def __post_init__(self):
        """Validate invariants"""
        if not self.street:
            raise ValueError("Street is required")
        if not self.city:
            raise ValueError("City is required")
        if not self.state:
            raise ValueError("State is required")
        if not self.postal_code:
            raise ValueError("Postal code is required")
        if not self.country:
            raise ValueError("Country is required")
    
    @property
    def formatted(self) -> str:
        """Format the address for display"""
        unit_part = f", Unit {self.unit}" if self.unit else ""
        return f"{self.street}{unit_part}, {self.city}, {self.state} {self.postal_code}, {self.country}"
```

#### 4.2.2 Entity Template

```python
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

@dataclass
class Product:
    """Product entity"""
    id: UUID = field(default_factory=uuid4)
    name: str
    description: str
    price: float
    stock_quantity: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None
    active: bool = True
    
    def __post_init__(self):
        """Validate invariants"""
        if not self.name:
            raise ValueError("Product name is required")
        if self.price < 0:
            raise ValueError("Price cannot be negative")
        if self.stock_quantity < 0:
            raise ValueError("Stock quantity cannot be negative")
    
    def update_price(self, new_price: float) -> None:
        """Update the product price"""
        if new_price < 0:
            raise ValueError("Price cannot be negative")
        self.price = new_price
        self.updated_at = datetime.now()
    
    def restock(self, quantity: int) -> None:
        """Add to the stock quantity"""
        if quantity <= 0:
            raise ValueError("Restock quantity must be positive")
        self.stock_quantity += quantity
        self.updated_at = datetime.now()
    
    def deactivate(self) -> None:
        """Deactivate the product"""
        self.active = False
        self.updated_at = datetime.now()
    
    def __eq__(self, other):
        if not isinstance(other, Product):
            return False
        return self.id == other.id
    
    def __hash__(self):
        return hash(self.id)
```

#### 4.2.3 Aggregate Root Template

```python
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional
from uuid import UUID, uuid4

@dataclass
class Order:
    """Order aggregate root"""
    id: UUID = field(default_factory=uuid4)
    customer_id: UUID
    items: List['OrderItem'] = field(default_factory=list)
    shipping_address: Optional[Address] = None
    status: str = "draft"
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None
    
    def add_item(self, product_id: UUID, product_name: str, price: float, quantity: int) -> None:
        """Add an item to the order"""
        # Business rule: Quantity must be positive
        if quantity <= 0:
            raise ValueError("Quantity must be positive")
            
        # Check for existing product in order
        for item in self.items:
            if item.product_id == product_id:
                # Update quantity instead of adding duplicate
                item.quantity += quantity
                self._update_timestamp()
                return
                
        # Add new item
        self.items.append(OrderItem(
            order_id=self.id,
            product_id=product_id,
            product_name=product_name,
            price=price,
            quantity=quantity
        ))
        self._update_timestamp()
    
    def remove_item(self, product_id: UUID) -> None:
        """Remove an item from the order"""
        # Find and remove the item
        initial_count = len(self.items)
        self.items = [item for item in self.items if item.product_id != product_id]
        
        # Check if item was found and removed
        if len(self.items) < initial_count:
            self._update_timestamp()
        else:
            raise ValueError(f"Product {product_id} not found in the order")
    
    def place(self) -> None:
        """Place the order"""
        # Business rule: Order must have items
        if not self.items:
            raise ValueError("Cannot place an empty order")
            
        # Business rule: Shipping address required
        if not self.shipping_address:
            raise ValueError("Shipping address is required")
            
        # Business rule: Order must be in draft status
        if self.status != "draft":
            raise ValueError(f"Cannot place order with status '{self.status}'")
            
        # Update status
        self.status = "placed"
        self._update_timestamp()
    
    def cancel(self) -> None:
        """Cancel the order"""
        # Business rule: Cannot cancel shipped orders
        if self.status == "shipped":
            raise ValueError("Cannot cancel an already shipped order")
            
        # Update status
        self.status = "cancelled"
        self._update_timestamp()
    
    def calculate_total(self) -> float:
        """Calculate the order total"""
        return sum(item.price * item.quantity for item in self.items)
    
    def _update_timestamp(self) -> None:
        """Update the updated_at timestamp"""
        self.updated_at = datetime.now()
    
    def __eq__(self, other):
        if not isinstance(other, Order):
            return False
        return self.id == other.id
    
    def __hash__(self):
        return hash(self.id)

@dataclass
class OrderItem:
    """Entity within Order aggregate"""
    order_id: UUID
    product_id: UUID
    product_name: str
    price: float
    quantity: int
    
    def __post_init__(self):
        """Validate invariants"""
        if self.price < 0:
            raise ValueError("Price cannot be negative")
        if self.quantity <= 0:
            raise ValueError("Quantity must be positive")
```

#### 4.2.4 Repository Template

```python
from abc import ABC, abstractmethod
from typing import List, Optional
from uuid import UUID

class OrderRepository(ABC):
    """Repository interface for Order aggregate"""
    
    @abstractmethod
    def save(self, order: Order) -> None:
        """Save an order to the repository"""
        pass
    
    @abstractmethod
    def get_by_id(self, order_id: UUID) -> Optional[Order]:
        """Get an order by its ID"""
        pass
    
    @abstractmethod
    def get_by_customer(self, customer_id: UUID) -> List[Order]:
        """Get all orders for a customer"""
        pass
    
    @abstractmethod
    def get_by_status(self, status: str) -> List[Order]:
        """Get all orders with a specific status"""
        pass

# SQLAlchemy implementation
class SQLAlchemyOrderRepository(OrderRepository):
    """SQLAlchemy implementation of OrderRepository"""
    
    def __init__(self, session):
        self.session = session
    
    def save(self, order: Order) -> None:
        """Save an order to the database"""
        self.session.add(order)
        self.session.commit()
    
    def get_by_id(self, order_id: UUID) -> Optional[Order]:
        """Get an order by its ID from the database"""
        return self.session.query(Order).filter_by(id=order_id).first()
    
    def get_by_customer(self, customer_id: UUID) -> List[Order]:
        """Get all orders for a customer from the database"""
        return self.session.query(Order).filter_by(customer_id=customer_id).all()
    
    def get_by_status(self, status: str) -> List[Order]:
        """Get all orders with a specific status from the database"""
        return self.session.query(Order).filter_by(status=status).all()
```

#### 4.2.5 Domain Service Template

```python
class InventoryService:
    """Domain service for inventory operations"""
    
    def __init__(self, product_repository):
        self.product_repository = product_repository
    
    def check_availability(self, order: Order) -> bool:
        """Check if all products in an order are available in sufficient quantity"""
        for item in order.items:
            product = self.product_repository.get_by_id(item.product_id)
            
            # Check if product exists and has sufficient quantity
            if not product or product.stock_quantity < item.quantity:
                return False
                
        return True
    
    def allocate_inventory(self, order: Order) -> bool:
        """Allocate inventory for an order"""
        # First check availability
        if not self.check_availability(order):
            return False
            
        # Allocate inventory
        for item in order.items:
            product = self.product_repository.get_by_id(item.product_id)
            product.stock_quantity -= item.quantity
            self.product_repository.save(product)
            
        return True
    
    def return_inventory(self, order: Order) -> None:
        """Return inventory for a cancelled order"""
        for item in order.items:
            product = self.product_repository.get_by_id(item.product_id)
            if product:
                product.stock_quantity += item.quantity
                self.product_repository.save(product)
```

#### 4.2.6 Application Service Template

```python
class OrderApplicationService:
    """Application service for order operations"""
    
    def __init__(
        self,
        order_repository,
        product_repository,
        inventory_service,
        payment_service,
        event_publisher
    ):
        self.order_repository = order_repository
        self.product_repository = product_repository
        self.inventory_service = inventory_service
        self.payment_service = payment_service
        self.event_publisher = event_publisher
    
    def create_order(self, customer_id: UUID) -> UUID:
        """Create a new order"""
        # Create order
        order = Order(customer_id=customer_id)
        
        # Save order
        self.order_repository.save(order)
        
        # Return order ID
        return order.id
    
    def add_item_to_order(
        self,
        order_id: UUID,
        product_id: UUID,
        quantity: int
    ) -> None:
        """Add an item to an order"""
        # Get order
        order = self.order_repository.get_by_id(order_id)
        if not order:
            raise ValueError(f"Order {order_id} not found")
            
        # Check order status
        if order.status != "draft":
            raise ValueError(f"Cannot add items to order with status '{order.status}'")
            
        # Get product
        product = self.product_repository.get_by_id(product_id)
        if not product:
            raise ValueError(f"Product {product_id} not found")
            
        # Add item to order
        order.add_item(
            product_id=product.id,
            product_name=product.name,
            price=product.price,
            quantity=quantity
        )
        
        # Save order
        self.order_repository.save(order)
    
    def place_order(
        self,
        order_id: UUID,
        shipping_address: Address
    ) -> bool:
        """Place an order"""
        # Get order
        order = self.order_repository.get_by_id(order_id)
        if not order:
            raise ValueError(f"Order {order_id} not found")
            
        # Set shipping address
        order.shipping_address = shipping_address
        
        # Check inventory
        if not self.inventory_service.check_availability(order):
            return False
            
        # Place order
        order.place()
        
        # Allocate inventory
        self.inventory_service.allocate_inventory(order)
        
        # Save order
        self.order_repository.save(order)
        
        # Publish event
        self.event_publisher.publish(OrderPlaced(
            order_id=order.id,
            customer_id=order.customer_id,
            total_amount=order.calculate_total()
        ))
        
        return True
    
    def cancel_order(self, order_id: UUID) -> None:
        """Cancel an order"""
        # Get order
        order = self.order_repository.get_by_id(order_id)
        if not order:
            raise ValueError(f"Order {order_id} not found")
            
        # Cancel order
        order.cancel()
        
        # Return inventory
        self.inventory_service.return_inventory(order)
        
        # Save order
        self.order_repository.save(order)
        
        # Publish event
        self.event_publisher.publish(OrderCancelled(
            order_id=order.id
        ))
```

### 4.3 Procedural Guides

#### 4.3.1 Identifying and Modeling Aggregates

1. **Identify business transactions**
   - What operations must succeed or fail as a unit?
   - What data must be consistent at all times?

2. **Find natural groups of entities**
   - Which entities are always accessed together?
   - Which entities share a lifecycle?

3. **Identify aggregate roots**
   - Which entity controls access to the group?
   - Which entity has a unique identity used for retrieval?

4. **Define aggregate boundaries**
   - What are the invariants that must be enforced?
   - How will entities within the aggregate reference each other?

5. **Reference other aggregates by identity only**
   - Use IDs to reference other aggregates
   - Avoid direct object references across aggregates

6. **Validate the aggregate design**
   - Is the aggregate focused on a specific capability?
   - Can it enforce all necessary invariants?
   - Is it a reasonable size for transactional and memory concerns?

#### 4.3.2 Implementing Repositories

1. **Define repository interfaces in the domain layer**
   - Create one repository per aggregate type
   - Define methods for common access patterns
   - Use repository methods that reflect domain concepts

2. **Create infrastructure implementations**
   - Implement repositories for your chosen persistence technology
   - Encapsulate all data access details
   - Handle mapping between domain and persistence models

3. **Design for optimistic concurrency**
   - Add version tracking for aggregates
   - Implement optimistic locking mechanisms

4. **Handle domain events**
   - Collect events from aggregates during transactions
   - Dispatch events after successful persistence

5. **Implement a Unit of Work pattern**
   - Coordinate multiple repository operations
   - Ensure transactional consistency
   - Simplify client code

#### 4.3.3 Integrating Bounded Contexts

1. **Identify relationship patterns**
   - Partnership, Customer-Supplier, Conformist, etc.
   - Determine integration requirements

2. **Define context boundaries**
   - Establish clear module/package/service boundaries
   - Document the ubiquitous language for each context

3. **Implement integration mechanisms**
   - For tightly coupled contexts: direct method calls or shared kernel
   - For loosely coupled contexts: messaging, events, or REST APIs
   - For protecting contexts: anti-corruption layers

4. **Create translation components**
   - Design mappers between different context models
   - Implement transformations of data between contexts

5. **Maintain the context map**
   - Document relationships between contexts
   - Update as the system evolves

### 4.4 Code Templates for Common DDD Scenarios

#### 4.4.1 Handling Money and Currency

```python
from dataclasses import dataclass
from decimal import Decimal
from typing import ClassVar, Set

@dataclass(frozen=True)
class Money:
    """Money value object"""
    amount: Decimal
    currency: str
    
    # Class-level constants
    VALID_CURRENCIES: ClassVar[Set[str]] = {'USD', 'EUR', 'GBP', 'JPY', 'CAD'}
    
    def __post_init__(self):
        """Validate invariants"""
        # Validate amount
        if self.amount < 0:
            raise ValueError("Amount cannot be negative")
        
        # Validate currency
        if self.currency not in self.VALID_CURRENCIES:
            raise ValueError(f"Currency must be one of: {self.VALID_CURRENCIES}")
        
        # Round to 2 decimal places (for most currencies)
        if self.currency != 'JPY':  # JPY doesn't use decimal places
            # Use object.__setattr__ since this is a frozen dataclass
            object.__setattr__(self, 'amount', self.amount.quantize(Decimal('0.01')))
    
    def __add__(self, other):
        """Add two money values"""
        if not isinstance(other, Money):
            return NotImplemented
        
        if self.currency != other.currency:
            raise ValueError(f"Cannot add {self.currency} to {other.currency}")
            
        return Money(amount=self.amount + other.amount, currency=self.currency)
    
    def __sub__(self, other):
        """Subtract two money values"""
        if not isinstance(other, Money):
            return NotImplemented
        
        if self.currency != other.currency:
            raise ValueError(f"Cannot subtract {other.currency} from {self.currency}")
            
        return Money(amount=self.amount - other.amount, currency=self.currency)
    
    def __mul__(self, multiplier):
        """Multiply money by a scalar"""
        if not isinstance(multiplier, (int, float, Decimal)):
            return NotImplemented
            
        return Money(
            amount=self.amount * Decimal(str(multiplier)),
            currency=self.currency
        )
    
    def allocate(self, ratios: list[int]) -> list['Money']:
        """Allocate money according to ratios"""
        if not ratios:
            return []
            
        total = sum(ratios)
        if total <= 0:
            raise ValueError("Sum of ratios must be positive")
            
        # Calculate the basic allocation
        results = []
        remainder = int(self.amount * 100)  # Work in cents to avoid floating point issues
        
        for ratio in ratios:
            share = int((Decimal(ratio) / Decimal(total)) * remainder)
            results.append(Money(Decimal(share) / 100, self.currency))
            remainder -= share
            
        # Distribute any remaining cents
        for i in range(remainder):
            results[i] = Money(results[i].amount + Decimal('0.01'), self.currency)
            
        return results
```

#### 4.4.2 Implementing a Shopping Cart

```python
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from uuid import UUID, uuid4

@dataclass
class ShoppingCart:
    """Shopping cart aggregate root"""
    id: UUID = field(default_factory=uuid4)
    customer_id: Optional[UUID] = None
    items: Dict[UUID, 'CartItem'] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    
    def __post_init__(self):
        """Initialize expiration time"""
        if not self.expires_at:
            # Set expiration 24 hours from creation
            self.expires_at = self.created_at + timedelta(hours=24)
    
    def add_item(self, product_id: UUID, product_name: str, price: Money, quantity: int = 1) -> None:
        """Add an item to the cart"""
        self._validate_cart_active()
        
        if quantity <= 0:
            raise ValueError("Quantity must be positive")
            
        # Check if product already in cart
        if product_id in self.items:
            # Update quantity
            self.items[product_id].quantity += quantity
        else:
            # Add new item
            self.items[product_id] = CartItem(
                product_id=product_id,
                product_name=product_name,
                price=price,
                quantity=quantity
            )
            
        self._update_timestamp()
    
    def remove_item(self, product_id: UUID) -> None:
        """Remove an item from the cart"""
        self._validate_cart_active()
        
        if product_id not in self.items:
            raise ValueError(f"Product {product_id} not in cart")
            
        del self.items[product_id]
        self._update_timestamp()
    
    def update_quantity(self, product_id: UUID, quantity: int) -> None:
        """Update the quantity of an item"""
        self._validate_cart_active()
        
        if quantity <= 0:
            # If quantity is zero or negative, remove the item
            self.remove_item(product_id)
            return
            
        if product_id not in self.items:
            raise ValueError(f"Product {product_id} not in cart")
            
        self.items[product_id].quantity = quantity
        self._update_timestamp()
    
    def clear(self) -> None:
        """Clear all items from the cart"""
        self.items.clear()
        self._update_timestamp()
    
    def calculate_total(self) -> Money:
        """Calculate the total price of items in the cart"""
        if not self.items:
            return Money(Decimal('0'), 'USD')  # Default empty cart value
            
        # Get the currency from the first item
        first_item = next(iter(self.items.values()))
        currency = first_item.price.currency
        
        # Sum all items
        total = sum(item.price.amount * item.quantity for item in self.items.values())
        
        return Money(total, currency)
    
    def is_empty(self) -> bool:
        """Check if the cart is empty"""
        return len(self.items) == 0
    
    def is_expired(self) -> bool:
        """Check if the cart is expired"""
        return datetime.now() > self.expires_at
    
    def assign_to_customer(self, customer_id: UUID) -> None:
        """Assign the cart to a customer"""
        self.customer_id = customer_id
        self._update_timestamp()
    
    def _update_timestamp(self) -> None:
        """Update the updated_at timestamp"""
        self.updated_at = datetime.now()
        # Reset expiration time when cart is updated
        self.expires_at = self.updated_at + timedelta(hours=24)
    
    def _validate_cart_active(self) -> None:
        """Validate that the cart is active (not expired)"""
        if self.is_expired():
            raise ValueError("Cannot modify an expired cart")

@dataclass
class CartItem:
    """Item in a shopping cart"""
    product_id: UUID
    product_name: str
    price: Money
    quantity: int
    
    def __post_init__(self):
        """Validate invariants"""
        if self.quantity <= 0:
            raise ValueError("Quantity must be positive")
    
    @property
    def total(self) -> Money:
        """Calculate the total price for this item"""
        return self.price * self.quantity
```

#### 4.4.3 Managing User Accounts and Authentication

```python
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto
from typing import List, Optional
from uuid import UUID, uuid4
import hashlib
import secrets

class UserRole(Enum):
    """User roles for authorization"""
    CUSTOMER = auto()
    ADMIN = auto()
    SUPPORT = auto()

@dataclass
class User:
    """User aggregate root"""
    id: UUID = field(default_factory=uuid4)
    email: str
    password_hash: str
    full_name: str
    roles: List[UserRole] = field(default_factory=lambda: [UserRole.CUSTOMER])
    active: bool = True
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None
    last_login: Optional[datetime] = None
    password_reset_token: Optional[str] = None
    password_reset_expires: Optional[datetime] = None
    
    @classmethod
    def create(cls, email: str, password: str, full_name: str) -> 'User':
        """Create a new user"""
        # Validate email
        if not is_valid_email(email):
            raise ValueError("Invalid email address")
            
        # Validate password strength
        if not is_strong_password(password):
            raise ValueError("Password does not meet strength requirements")
            
        # Hash password
        password_hash = hash_password(password)
        
        return cls(
            email=email.lower(),
            password_hash=password_hash,
            full_name=full_name
        )
    
    def authenticate(self, password: str) -> bool:
        """Authenticate a user"""
        if not self.active:
            return False
            
        if verify_password(self.password_hash, password):
            self.last_login = datetime.now()
            return True
            
        return False
    
    def change_password(self, current_password: str, new_password: str) -> bool:
        """Change a user's password"""
        # Verify current password
        if not verify_password(self.password_hash, current_password):
            return False
            
        # Validate new password strength
        if not is_strong_password(new_password):
            raise ValueError("New password does not meet strength requirements")
            
        # Set new password
        self.password_hash = hash_password(new_password)
        self.updated_at = datetime.now()
        self.password_reset_token = None
        self.password_reset_expires = None
        
        return True
    
    def initiate_password_reset(self) -> str:
        """Initiate a password reset"""
        # Generate token
        token = secrets.token_urlsafe(32)
        
        # Set token and expiration
        self.password_reset_token = token
        self.password_reset_expires = datetime.now() + timedelta(hours=24)
        
        return token
    
    def reset_password(self, token: str, new_password: str) -> bool:
        """Reset a password with a token"""
        # Verify token and expiration
        if not self.password_reset_token or self.password_reset_token != token:
            return False
            
        if not self.password_reset_expires or datetime.now() > self.password_reset_expires:
            return False
            
        # Validate new password
        if not is_strong_password(new_password):
            raise ValueError("New password does not meet strength requirements")
            
        # Set new password
        self.password_hash = hash_password(new_password)
        self.updated_at = datetime.now()
        self.password_reset_token = None
        self.password_reset_expires = None
        
        return True
    
    def add_role(self, role: UserRole) -> None:
        """Add a role to the user"""
        if role not in self.roles:
            self.roles.append(role)
            self.updated_at = datetime.now()
    
    def remove_role(self, role: UserRole) -> None:
        """Remove a role from the user"""
        if role in self.roles:
            self.roles.remove(role)
            self.updated_at = datetime.now()
    
    def has_role(self, role: UserRole) -> bool:
        """Check if the user has a specific role"""
        return role in self.roles
    
    def deactivate(self) -> None:
        """Deactivate the user account"""
        self.active = False
        self.updated_at = datetime.now()
    
    def activate(self) -> None:
        """Activate the user account"""
        self.active = True
        self.updated_at = datetime.now()

# Helper functions for user management
def is_valid_email(email: str) -> bool:
    """Validate email format"""
    # Simple regex validation for example purposes
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

def is_strong_password(password: str) -> bool:
    """Check if a password is strong enough"""
    # At least 8 characters, containing uppercase, lowercase, and number
    if len(password) < 8:
        return False
        
    if not any(c.isupper() for c in password):
        return False
        
    if not any(c.islower() for c in password):
        return False
        
    if not any(c.isdigit() for c in password):
        return False
        
    return True

def hash_password(password: str) -> str:
    """Hash a password using a secure algorithm"""
    # In production, use a proper password hashing library like bcrypt
    # This is a simplified example
    salt = secrets.token_hex(16)
    pw_hash = hashlib.sha256((password + salt).encode()).hexdigest()
    return f"{salt}${pw_hash}"

def verify_password(stored_hash: str, provided_password: str) -> bool:
    """Verify a password against its hash"""
    # In production, use a proper password verification from a library like bcrypt
    # This is a simplified example
    salt, hash_value = stored_hash.split('$')
    computed_hash = hashlib.sha256((provided_password + salt).encode()).hexdigest()
    return computed_hash == hash_value
```

#### 4.4.4 Implementing Domain Events

```python
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Type
from uuid import UUID, uuid4

# 1. Domain Event definitions
@dataclass(frozen=True)
class DomainEvent:
    """Base class for all domain events"""
    id: UUID = field(default_factory=uuid4)
    occurred_on: datetime = field(default_factory=datetime.now)

@dataclass(frozen=True)
class OrderPlaced(DomainEvent):
    """Event indicating an order has been placed"""
    order_id: UUID
    customer_id: UUID
    total_amount: float

@dataclass(frozen=True)
class OrderShipped(DomainEvent):
    """Event indicating an order has been shipped"""
    order_id: UUID
    tracking_number: str
    carrier: str

@dataclass(frozen=True)
class OrderCancelled(DomainEvent):
    """Event indicating an order has been cancelled"""
    order_id: UUID
    reason: str

# 2. Event Publisher
class DomainEventPublisher:
    """Simple in-memory event publisher"""
    
    def __init__(self):
        self.handlers: Dict[Type[DomainEvent], List[callable]] = {}
    
    def register(self, event_type: Type[DomainEvent], handler: callable) -> None:
        """Register a handler for an event type"""
        if event_type not in self.handlers:
            self.handlers[event_type] = []
        self.handlers[event_type].append(handler)
    
    def publish(self, event: DomainEvent) -> None:
        """Publish an event to all registered handlers"""
        event_type = type(event)
        
        # Call handlers registered for this event type
        for handler in self.handlers.get(event_type, []):
            handler(event)
        
        # Call handlers registered for all events
        for handler in self.handlers.get(DomainEvent, []):
            handler(event)

# 3. Aggregate Root with events
@dataclass
class AggregateRoot:
    """Base class for aggregate roots with domain events"""
    _events: List[DomainEvent] = field(default_factory=list, init=False, repr=False)
    
    def add_event(self, event: DomainEvent) -> None:
        """Add a domain event to this aggregate"""
        self._events.append(event)
    
    def clear_events(self) -> List[DomainEvent]:
        """Clear and return all events from this aggregate"""
        events = list(self._events)
        self._events.clear()
        return events

@dataclass
class Order(AggregateRoot):
    """Order aggregate with domain events"""
    id: UUID = field(default_factory=uuid4)
    customer_id: UUID
    items: List['OrderItem'] = field(default_factory=list)
    status: str = "draft"
    
    def place(self) -> None:
        """Place the order"""
        if not self.items:
            raise ValueError("Cannot place an empty order")
            
        self.status = "placed"
        
        # Add domain event
        self.add_event(OrderPlaced(
            order_id=self.id,
            customer_id=self.customer_id,
            total_amount=self.calculate_total()
        ))
    
    def ship(self, tracking_number: str, carrier: str) -> None:
        """Ship the order"""
        if self.status != "placed":
            raise ValueError(f"Cannot ship order with status '{self.status}'")
            
        self.status = "shipped"
        
        # Add domain event
        self.add_event(OrderShipped(
            order_id=self.id,
            tracking_number=tracking_number,
            carrier=carrier
        ))
    
    def cancel(self, reason: str) -> None:
        """Cancel the order"""
        if self.status == "shipped":
            raise ValueError("Cannot cancel a shipped order")
            
        self.status = "cancelled"
        
        # Add domain event
        self.add_event(OrderCancelled(
            order_id=self.id,
            reason=reason
        ))
    
    def calculate_total(self) -> float:
        """Calculate the order total"""
        return sum(item.price * item.quantity for item in self.items)

# 4. Event Handlers
def order_placed_email_handler(event: OrderPlaced) -> None:
    """Send an email notification when an order is placed"""
    print(f"Sending email to customer {event.customer_id} for order {event.order_id}")
    # Email sending logic here

def order_placed_inventory_handler(event: OrderPlaced) -> None:
    """Allocate inventory when an order is placed"""
    print(f"Allocating inventory for order {event.order_id}")
    # Inventory allocation logic here

def order_shipped_notification_handler(event: OrderShipped) -> None:
    """Notify customer when an order ships"""
    print(f"Notifying customer about shipment of order {event.order_id}")
    print(f"Tracking number: {event.tracking_number} via {event.carrier}")
    # Notification logic here

def event_logging_handler(event: DomainEvent) -> None:
    """Log all domain events"""
    print(f"[LOG] {type(event).__name__} at {event.occurred_on}: {event}")
    # Logging logic here

# 5. Repository with event publishing
class OrderRepository:
    """Repository for orders with event publishing"""
    
    def __init__(self, session, event_publisher: DomainEventPublisher):
        self.session = session
        self.event_publisher = event_publisher
    
    def save(self, order: Order) -> None:
        """Save an order and publish its events"""
        # Save order to database
        self.session.add(order)
        
        # Collect events
        events = order.clear_events()
        
        # Commit transaction
        self.session.commit()
        
        # Publish events after successful commit
        for event in events:
            self.event_publisher.publish(event)
    
    def get_by_id(self, order_id: UUID) -> Order:
        """Get an order by ID"""
        return self.session.query(Order).filter_by(id=order_id).first()

# 6. Setting up the event system
publisher = DomainEventPublisher()

# Register handlers
publisher.register(OrderPlaced, order_placed_email_handler)
publisher.register(OrderPlaced, order_placed_inventory_handler)
publisher.register(OrderShipped, order_shipped_notification_handler)
publisher.register(DomainEvent, event_logging_handler)
```

#### 4.4.5 Setting Up SQLAlchemy for DDD

```python
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional
from uuid import UUID, uuid4

from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime, ForeignKey, 
    create_engine, Table, MetaData
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, registry, sessionmaker, scoped_session
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID

# 1. Domain model (independent of persistence)
@dataclass
class Customer:
    """Customer aggregate root"""
    id: UUID = field(default_factory=uuid4)
    name: str
    email: str
    active: bool = True
    created_at: datetime = field(default_factory=datetime.now)

@dataclass
class Order:
    """Order aggregate root"""
    id: UUID = field(default_factory=uuid4)
    customer_id: UUID
    status: str = "draft"
    created_at: datetime = field(default_factory=datetime.now)
    items: List['OrderItem'] = field(default_factory=list)
    
    def add_item(self, product_id: UUID, quantity: int, price: float) -> None:
        """Add an item to the order"""
        self.items.append(OrderItem(
            order_id=self.id,
            product_id=product_id,
            quantity=quantity,
            price=price
        ))
    
    def place(self) -> None:
        """Place the order"""
        if not self.items:
            raise ValueError("Cannot place an empty order")
        
        self.status = "placed"

@dataclass
class OrderItem:
    """Order item entity"""
    order_id: UUID
    product_id: UUID
    quantity: int
    price: float
    id: UUID = field(default_factory=uuid4)

# 2. SQLAlchemy setup
Base = declarative_base()
metadata = MetaData()

# 3. Database models (ORM)
class CustomerModel(Base):
    """SQLAlchemy model for Customer"""
    __tablename__ = "customers"
    
    id = Column(PostgresUUID(as_uuid=True), primary_key=True)
    name = Column(String, nullable=False)
    email = Column(String, nullable=False, unique=True)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)

class OrderModel(Base):
    """SQLAlchemy model for Order"""
    __tablename__ = "orders"
    
    id = Column(PostgresUUID(as_uuid=True), primary_key=True)
    customer_id = Column(PostgresUUID(as_uuid=True), ForeignKey("customers.id"))
    status = Column(String, default="draft")
    created_at = Column(DateTime, default=datetime.now)
    
    items = relationship("OrderItemModel", back_populates="order", cascade="all, delete-orphan")
    customer = relationship("CustomerModel")

class OrderItemModel(Base):
    """SQLAlchemy model for OrderItem"""
    __tablename__ = "order_items"
    
    id = Column(PostgresUUID(as_uuid=True), primary_key=True)
    order_id = Column(PostgresUUID(as_uuid=True), ForeignKey("orders.id"))
    product_id = Column(PostgresUUID(as_uuid=True), nullable=False)
    quantity = Column(Integer, nullable=False)
    price = Column(Float, nullable=False)
    
    order = relationship("OrderModel", back_populates="items")

# 4. Repository implementations
class CustomerRepository:
    """Repository for Customer aggregate"""
    
    def __init__(self, session):
        self.session = session
    
    def add(self, customer: Customer) -> None:
        """Add a new customer"""
        # Convert domain object to ORM model
        customer_model = CustomerModel(
            id=customer.id,
            name=customer.name,
            email=customer.email,
            active=customer.active,
            created_at=customer.created_at
        )
        
        self.session.add(customer_model)
        self.session.commit()
    
    def get_by_id(self, customer_id: UUID) -> Optional[Customer]:
        """Get a customer by ID"""
        customer_model = self.session.query(CustomerModel).get(customer_id)
        
        if not customer_model:
            return None
            
        # Convert ORM model to domain object
        return Customer(
            id=customer_model.id,
            name=customer_model.name,
            email=customer_model.email,
            active=customer_model.active,
            created_at=customer_model.created_at
        )
    
    def get_by_email(self, email: str) -> Optional[Customer]:
        """Get a customer by email"""
        customer_model = self.session.query(CustomerModel).filter_by(email=email).first()
        
        if not customer_model:
            return None
            
        # Convert ORM model to domain object
        return Customer(
            id=customer_model.id,
            name=customer_model.name,
            email=customer_model.email,
            active=customer_model.active,
            created_at=customer_model.created_at
        )

class OrderRepository:
    """Repository for Order aggregate"""
    
    def __init__(self, session):
        self.session = session
    
    def add(self, order: Order) -> None:
        """Add a new order"""
        # Convert domain object to ORM model
        order_model = OrderModel(
            id=order.id,
            customer_id=order.customer_id,
            status=order.status,
            created_at=order.created_at
        )
        
        # Add order items
        for item in order.items:
            order_item_model = OrderItemModel(
                id=item.id,
                order_id=order.id,
                product_id=item.product_id,
                quantity=item.quantity,
                price=item.price
            )
            order_model.items.append(order_item_model)
        
        self.session.add(order_model)
        self.session.commit()
    
    def get_by_id(self, order_id: UUID) -> Optional[Order]:
        """Get an order by ID"""
        order_model = self.session.query(OrderModel).options(
            # eager load relationship to avoid N+1 queries
            sqlalchemy.orm.joinedload(OrderModel.items)
        ).get(order_id)
        
        if not order_model:
            return None
            
        # Convert ORM model to domain object
        order = Order(
            id=order_model.id,
            customer_id=order_model.customer_id,
            status=order_model.status,
            created_at=order_model.created_at,
            items=[]
        )
        
        # Convert order items
        for item_model in order_model.items:
            order.items.append(OrderItem(
                id=item_model.id,
                order_id=item_model.order_id,
                product_id=item_model.product_id,
                quantity=item_model.quantity,
                price=item_model.price
            ))
            
        return order
    
    def update(self, order: Order) -> None:
        """Update an existing order"""
        # Get existing order model
        order_model = self.session.query(OrderModel).get(order.id)
        
        if not order_model:
            raise ValueError(f"Order {order.id} not found")
            
        # Update fields
        order_model.status = order.status
        
        # Update items (this is simplified - a real implementation would handle additions/removals better)
        
        # Clear existing items
        order_model.items = []
        
        # Add current items
        for item in order.items:
            order_item_model = OrderItemModel(
                id=item.id,
                order_id=order.id,
                product_id=item.product_id,
                quantity=item.quantity,
                price=item.price
            )
            order_model.items.append(order_item_model)
        
        self.session.commit()

# 5. Database setup and session management
def create_db_session():
    """Set up database connection and session factory"""
    # Create engine
    engine = create_engine(
        "postgresql://username:password@localhost/dbname",
        echo=True  # Set to False in production
    )
    
    # Create tables
    Base.metadata.create_all(engine)
    
    # Create session factory
    session_factory = sessionmaker(bind=engine)
    
    # Create thread-local session
    return scoped_session(session_factory)

# 6. Using the repository with Unit of Work pattern
class UnitOfWork:
    """Unit of Work for managing database transactions"""
    
    def __init__(self, session_factory):
        self.session_factory = session_factory
    
    def __enter__(self):
        self.session = self.session_factory()
        self.customers = CustomerRepository(self.session)
        self.orders = OrderRepository(self.session)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            # An exception occurred - rollback
            self.session.rollback()
        else:
            # No exception - commit
            self.session.commit()
        
        # Always close the session
        self.session.close()

# 7. Example usage
def create_order(customer_email: str, order_items: list) -> UUID:
    """Create a new order for a customer"""
    session_factory = create_db_session()
    
    with UnitOfWork(session_factory) as uow:
        # Get customer
        customer = uow.customers.get_by_email(customer_email)
        
        if not customer:
            raise ValueError(f"Customer with email {customer_email} not found")
            
        # Create order
        order = Order(customer_id=customer.id)
        
        # Add items
        for item in order_items:
            order.add_item(
                product_id=item["product_id"],
                quantity=item["quantity"],
                price=item["price"]
            )
            
        # Place order
        order.place()
        
        # Save order
        uow.orders.add(order)
        
        return order.id

### 4.5 Testing DDD Components

Testing is critical for verifying that domain logic correctly enforces business rules. Here are templates for testing different DDD components.

#### 4.5.1 Testing Value Objects

```python
import pytest
from decimal import Decimal
from uuid import uuid4
from domain.model.value_objects import Money, Address

class TestMoneyValueObject:
    def test_creates_money_with_valid_input(self):
        # Arrange & Act
        money = Money(amount=Decimal('10.50'), currency='USD')
        
        # Assert
        assert money.amount == Decimal('10.50')
        assert money.currency == 'USD'
    
    def test_rejects_negative_amount(self):
        # Arrange & Act & Assert
        with pytest.raises(ValueError) as exc_info:
            Money(amount=Decimal('-10.50'), currency='USD')
            
        assert "Amount cannot be negative" in str(exc_info.value)
    
    def test_rejects_invalid_currency(self):
        # Arrange & Act & Assert
        with pytest.raises(ValueError) as exc_info:
            Money(amount=Decimal('10.50'), currency='XYZ')
            
        assert "Currency must be" in str(exc_info.value)
    
    def test_adding_same_currency(self):
        # Arrange
        money1 = Money(amount=Decimal('10.50'), currency='USD')
        money2 = Money(amount=Decimal('5.75'), currency='USD')
        
        # Act
        result = money1 + money2
        
        # Assert
        assert result.amount == Decimal('16.25')
        assert result.currency == 'USD'
    
    def test_adding_different_currencies_raises_error(self):
        # Arrange
        money1 = Money(amount=Decimal('10.50'), currency='USD')
        money2 = Money(amount=Decimal('5.75'), currency='EUR')
        
        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            result = money1 + money2
            
        assert "Cannot add" in str(exc_info.value)
```

#### 4.5.2 Testing Entities and Aggregates

```python
import pytest
from decimal import Decimal
from uuid import uuid4
from domain.model.aggregates import Order, OrderItem
from domain.model.value_objects import Money, Address

class TestOrderAggregate:
    def test_creates_order_with_valid_input(self):
        # Arrange
        customer_id = uuid4()
        
        # Act
        order = Order(customer_id=customer_id)
        
        # Assert
        assert order.customer_id == customer_id
        assert order.status == "draft"
        assert len(order.items) == 0
    
    def test_adds_item_to_order(self):
        # Arrange
        order = Order(customer_id=uuid4())
        product_id = uuid4()
        
        # Act
        order.add_item(
            product_id=product_id,
            product_name="Test Product",
            price=Money(Decimal('10.00'), 'USD'),
            quantity=2
        )
        
        # Assert
        assert len(order.items) == 1
        assert order.items[0].product_id == product_id
        assert order.items[0].quantity == 2
        assert order.items[0].price.amount == Decimal('10.00')
    
    def test_calculate_total(self):
        # Arrange
        order = Order(customer_id=uuid4())
        
        # Add multiple items
        order.add_item(
            product_id=uuid4(),
            product_name="Product 1",
            price=Money(Decimal('10.00'), 'USD'),
            quantity=2
        )
        
        order.add_item(
            product_id=uuid4(),
            product_name="Product 2",
            price=Money(Decimal('15.50'), 'USD'),
            quantity=1
        )
        
        # Act
        total = order.calculate_total()
        
        # Assert
        assert total.amount == Decimal('35.50')
        assert total.currency == 'USD'
    
    def test_place_order_with_items(self):
        # Arrange
        order = Order(customer_id=uuid4())
        order.add_item(
            product_id=uuid4(),
            product_name="Test Product",
            price=Money(Decimal('10.00'), 'USD'),
            quantity=2
        )
        order.shipping_address = Address(
            street="123 Main St",
            city="Anytown",
            state="CA",
            postal_code="12345",
            country="US"
        )
        
        # Act
        order.place()
        
        # Assert
        assert order.status == "placed"
    
    def test_place_empty_order_raises_error(self):
        # Arrange
        order = Order(customer_id=uuid4())
        order.shipping_address = Address(
            street="123 Main St",
            city="Anytown",
            state="CA",
            postal_code="12345",
            country="US"
        )
        
        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            order.place()
            
        assert "Cannot place an empty order" in str(exc_info.value)
    
    def test_place_order_without_address_raises_error(self):
        # Arrange
        order = Order(customer_id=uuid4())
        order.add_item(
            product_id=uuid4(),
            product_name="Test Product",
            price=Money(Decimal('10.00'), 'USD'),
            quantity=2
        )
        
        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            order.place()
            
        assert "Shipping address is required" in str(exc_info.value)
```

#### 4.5.3 Testing Domain Services

```python
import pytest
from decimal import Decimal
from uuid import uuid4
from domain.model.aggregates import Order, Product
from domain.model.value_objects import Money
from domain.services.inventory_service import InventoryService

# Test doubles
class MockProductRepository:
    def __init__(self, products=None):
        self.products = products or {}
    
    def get_by_id(self, product_id):
        return self.products.get(product_id)
    
    def save(self, product):
        self.products[product.id] = product

class TestInventoryService:
    def test_check_availability_with_sufficient_stock(self):
        # Arrange
        # Create test products
        product1_id = uuid4()
        product2_id = uuid4()
        
        products = {
            product1_id: Product(
                id=product1_id,
                name="Product 1",
                price=Money(Decimal('10.00'), 'USD'),
                stock_quantity=10
            ),
            product2_id: Product(
                id=product2_id,
                name="Product 2",
                price=Money(Decimal('15.50'), 'USD'),
                stock_quantity=5
            )
        }
        
        # Create repository with test products
        product_repository = MockProductRepository(products)
        
        # Create service with mock repository
        inventory_service = InventoryService(product_repository)
        
        # Create order with items
        order = Order(customer_id=uuid4())
        order.add_item(
            product_id=product1_id,
            product_name="Product 1",
            price=Money(Decimal('10.00'), 'USD'),
            quantity=3  # Less than available stock
        )
        order.add_item(
            product_id=product2_id,
            product_name="Product 2",
            price=Money(Decimal('15.50'), 'USD'),
            quantity=2  # Less than available stock
        )
        
        # Act
        result = inventory_service.check_availability(order)
        
        # Assert
        assert result is True
    
    def test_check_availability_with_insufficient_stock(self):
        # Arrange
        # Create test products
        product1_id = uuid4()
        product2_id = uuid4()
        
        products = {
            product1_id: Product(
                id=product1_id,
                name="Product 1",
                price=Money(Decimal('10.00'), 'USD'),
                stock_quantity=10
            ),
            product2_id: Product(
                id=product2_id,
                name="Product 2",
                price=Money(Decimal('15.50'), 'USD'),
                stock_quantity=1  # Not enough stock
            )
        }
        
        # Create repository with test products
        product_repository = MockProductRepository(products)
        
        # Create service with mock repository
        inventory_service = InventoryService(product_repository)
        
        # Create order with items
        order = Order(customer_id=uuid4())
        order.add_item(
            product_id=product1_id,
            product_name="Product 1",
            price=Money(Decimal('10.00'), 'USD'),
            quantity=3  # Less than available stock
        )
        order.add_item(
            product_id=product2_id,
            product_name="Product 2",
            price=Money(Decimal('15.50'), 'USD'),
            quantity=2  # More than available stock
        )
        
        # Act
        result = inventory_service.check_availability(order)
        
        # Assert
        assert result is False
    
    def test_allocate_inventory_reduces_stock(self):
        # Arrange
        # Create test products
        product1_id = uuid4()
        product2_id = uuid4()
        
        products = {
            product1_id: Product(
                id=product1_id,
                name="Product 1",
                price=Money(Decimal('10.00'), 'USD'),
                stock_quantity=10
            ),
            product2_id: Product(
                id=product2_id,
                name="Product 2",
                price=Money(Decimal('15.50'), 'USD'),
                stock_quantity=5
            )
        }
        
        # Create repository with test products
        product_repository = MockProductRepository(products)
        
        # Create service with mock repository
        inventory_service = InventoryService(product_repository)
        
        # Create order with items
        order = Order(customer_id=uuid4())
        order.add_item(
            product_id=product1_id,
            product_name="Product 1",
            price=Money(Decimal('10.00'), 'USD'),
            quantity=3
        )
        order.add_item(
            product_id=product2_id,
            product_name="Product 2",
            price=Money(Decimal('15.50'), 'USD'),
            quantity=2
        )
        
        # Act
        inventory_service.allocate_inventory(order)
        
        # Assert
        assert products[product1_id].stock_quantity == 7  # 10 - 3
        assert products[product2_id].stock_quantity == 3  # 5 - 2
```

#### 4.5.4 Testing Repositories

```python
import pytest
from uuid import uuid4
from domain.model.aggregates import Order, OrderItem
from domain.model.value_objects import Money, Address
from infrastructure.repositories.order_repository import SQLAlchemyOrderRepository

# Test requires a database, so integration test
# Can use in-memory SQLite for testing
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from infrastructure.persistence.models import Base

class TestOrderRepository:
    @pytest.fixture
    def session(self):
        """Create an in-memory database session for testing"""
        engine = create_engine('sqlite:///:memory:')
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)
        session = Session()
        yield session
        session.close()
    
    @pytest.fixture
    def repository(self, session):
        """Create a repository with the test session"""
        return SQLAlchemyOrderRepository(session)
    
    def test_save_and_get_order(self, repository):
        # Arrange
        customer_id = uuid4()
        order = Order(customer_id=customer_id)
        
        product_id = uuid4()
        order.add_item(
            product_id=product_id,
            product_name="Test Product",
            price=Money(Decimal('10.00'), 'USD'),
            quantity=2
        )
        
        # Act
        repository.add(order)
        retrieved_order = repository.get_by_id(order.id)
        
        # Assert
        assert retrieved_order is not None
        assert retrieved_order.id == order.id
        assert retrieved_order.customer_id == customer_id
        assert len(retrieved_order.items) == 1
        assert retrieved_order.items[0].product_id == product_id
        assert retrieved_order.items[0].quantity == 2
        assert retrieved_order.items[0].price == 10.00
    
    def test_update_order(self, repository):
        # Arrange
        customer_id = uuid4()
        order = Order(customer_id=customer_id)
        
        product_id = uuid4()
        order.add_item(
            product_id=product_id,
            product_name="Test Product",
            price=Money(Decimal('10.00'), 'USD'),
            quantity=2
        )
        
        # Save initial state
        repository.add(order)
        
        # Modify order
        order.status = "placed"
        
        # Act
        repository.update(order)
        retrieved_order = repository.get_by_id(order.id)
        
        # Assert
        assert retrieved_order.status == "placed"
```

## Conclusion

This comprehensive framework provides a practical approach to implementing Domain-Driven Design in Python 3.12 applications. By focusing on the core concepts and providing concrete implementations, it enables developers to create software that accurately reflects and solves complex business problems.

DDD is not a one-size-fits-all solution, and not every project will benefit from its full implementation. However, the principles and patterns of DDD can be selectively applied to improve the design and maintainability of many software systems.

Remember these key principles:

1. Focus on the domain, not the technology
2. Collaborate with domain experts to develop a shared understanding
3. Use a ubiquitous language throughout the codebase and communication
4. Create bounded contexts with clear boundaries
5. Model the domain with entities, value objects, and aggregates
6. Protect domain logic from infrastructure concerns
7. Continuously refine the model as understanding evolves

By following this framework, you'll be well-equipped to implement DDD in your Python projects, creating more maintainable, adaptable, and business-aligned software.