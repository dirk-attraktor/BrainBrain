from django.contrib import admin

# Register your models here.
from .models import Problem
from .models import Species
from .models import Population
from .models import Individual
from .models import ReferenceFunction
from .models import Peer

admin.site.register(Problem)
admin.site.register(Species)
admin.site.register(Population)
admin.site.register(Individual)
admin.site.register(ReferenceFunction)
admin.site.register(Peer)
