## Web Application based on Python3.

### Compared with the tutorial, the new features of this application include：

* **delete a registered user account:** Once the user account is deleted, its comments are still maintained; but the user name will be marked with "deleted";
* **improve the management of comments:** Once a article is deleted，its corresponding comments are removed either;
* **improve the backstage management system:** On the page of "comment management", users may directly see the article names from which that comment come; users may directly access those articles by clicking their names;
* **item information:** show number of all items, current number or other information;
* **new contents:** more sections such "about author" and "study in US"

**Note**: 4 REST APIs are provided for future development：

* `/api/blogs/{id}`：get the blog with a specified ID
* `/api/blogs`：get blogs on the first page (by default)
* `/api/comments`：get comments on the first page (by default)
* `/api/users`：get users on the first page (by default); passwords are blocked

Contact author：<dingyihang1994@gmail.com>