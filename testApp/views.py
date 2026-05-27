from rest_framework.views import APIView

from testApp.models import Book
from testApp.serializers import BookSerializer
from .mixins import *

# class BookAPIView(APIView):
#     def get(self,request):
#         books = Book.objects.all()
        
#         data = []
#         for book in books:
#             data.append({
#                 "id":book.id,
#                 "title":book.title,
#                 "author":book.author,
#                 "price": str(book.price),
#                 "is_published":book.is_published 
#             })
#         return custom200("Get rquest recieved",data)
    
#     def post(self, request):
#         data = request.data
        
#         book = Book.objects.create(
#             title=data.get('title'),
#             author=data.get('author'),
#             price=data.get('price'),
#             is_published = data.get('is_published',True)
#         )
#         return custom201("Post request recieved",book.id)


class BookAPIView(APIView):
    def get(self,request):
        books = Book.objects.all()
        serializer = BookSerializer(books, many=True) # serialize
        return custom200("Books fetched successfully",serializer.data)
    
    def post(self, request):
        serializer = BookSerializer(data=request.data) # deserialize
        
        if serializer.is_valid():
            serializer.save()
            return custom201("Book created successfully",serializer.data)
        return custom400("Failed to create book",serializer.errors)
    
    
from django.http import JsonResponse
from django.contrib.auth.models import User

def internal_user_count(request):
    """Secure endpoint used by the sidecar server to check DB stats."""
    count = User.objects.count()
    return JsonResponse({"count": count})
