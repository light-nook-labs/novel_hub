from django.shortcuts import render
from django.http import HttpResponse

from .models import Tag, Author, Novel, Contest, Noveltaglink


# Create your views here.
def home(request):
    num_novels = Novel.objects.count()
    num_tags = Tag.objects.count()
    num_authors = Author.objects.count()
    num_contests = Contest.objects.count()
    # return HttpResponse(f"<h1>Hello Django {num_novels}</h1>")
    context = {
        "num_authors": num_authors,
        "num_contests": num_contests,
        "num_novels": num_novels,
        "num_tags": num_tags,
    }
    return render(request, "novel/base.html", context)
